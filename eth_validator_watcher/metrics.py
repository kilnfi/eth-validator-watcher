import logging
import os

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import batched

from multiprocessing import Pool
from prometheus_client import Counter, Gauge

from .watched_validators import WatchedValidator


NB_THREADS = 4


# This is global because Prometheus metrics don't support registration
# multiple times. This is a workaround for unit tests.
_metrics = None


@dataclass
class PrometheusMetrics:
    """Define the Prometheus metrics.
    """
    eth_slot: Gauge
    eth_epoch: Gauge
    eth_current_price_dollars: Gauge

    eth_validator_status_count: Gauge
    eth_suboptimal_sources_rate: Gauge
    eth_suboptimal_targets_rate: Gauge
    eth_suboptimal_heads_rate: Gauge
    eth_consensus_rewards_rate: Gauge
    eth_ideal_consensus_rewards_gwei: Gauge
    eth_actual_consensus_rewards_gwei: Gauge
    eth_missed_attestations_count: Gauge
    eth_missed_consecutive_attestations_count: Gauge
    eth_slashed_validators_count: Gauge
    
    eth_block_proposals_head_total: Counter
    eth_missed_block_proposals_head_total: Counter
    eth_block_proposals_finalized_total: Counter
    eth_missed_block_proposals_finalized_total: Counter

    eth_future_block_proposals: Gauge

  
@dataclass
class AggregatedMetricsByLabel():
    """Helper class used to aggregate metrics by label.
    """
    # Count of validators by status
    validator_status_count: dict[str, int] = field(default_factory=dict)

    # Gauges
    suboptimal_source_count: int = 0
    suboptimal_target_count: int = 0
    suboptimal_head_count: int = 0
    optimal_source_count: int = 0
    optimal_target_count: int = 0
    optimal_head_count: int = 0
    validator_slashes: int = 0
        
    # Gauges
    ideal_consensus_reward: int = 0
    actual_consensus_reward: int = 0
    missed_attestations: int = 0
    missed_consecutive_attestations: int = 0
            
    # Counters
    proposed_blocks: int = 0
    missed_blocks: int = 0
    proposed_finalized_blocks: int = 0
    missed_finalized_blocks: int = 0

    # Gauge
    future_blocks: int = 0


def _aggregate_validator_metrics(validators: list[WatchedValidator]) -> dict[str, AggregatedMetricsByLabel]:
    """Compute the metrics from a list of validators.

    This is called in a parallel unix process so that we can scale
    with the number of validators on the network (with a single CPU it
    takes about 5 seconds to go through 1.5M validators). Do not try
    to change the state of validators here as it will be lost. The
    resulting dictionnary is then merged in the main thread.

    Parameters:
    validators: list[WatchedValidator]

    Returns:
    dict[str, AggregatedMetricsByLabel]
    """
    logging.info(f'New thread aggregating data from {len(validators)} validators')

    metrics = defaultdict(AggregatedMetricsByLabel)

    for validator in validators:

        status = str(validator.status)

        for label in validator.labels:
            m = metrics[label]

            if status not in m.validator_status_count:
                m.validator_status_count[status] = 0
            m.validator_status_count[status] += 1
 
            m.validator_slashes += int(validator.beacon_validator.validator.slashed == True)

            # Everything below implies to have a validator that is
            # active on the beacon chain, this prevents
            # miscounting missed attestation for instance.

            if not validator.is_validating():
                continue

            # Looks weird but we want to explicitly have labels set
            # for each set of labels even if they aren't validating
            # (in which case the validator attributes are None).

            m.suboptimal_source_count += int(validator.suboptimal_source == True)
            m.suboptimal_target_count += int(validator.suboptimal_target == True)
            m.suboptimal_head_count += int(validator.suboptimal_head == True)
            m.optimal_source_count += int(validator.suboptimal_source == False)
            m.optimal_target_count += int(validator.suboptimal_target == False)
            m.optimal_head_count += int(validator.suboptimal_head == False)

            m.ideal_consensus_reward += validator.ideal_consensus_reward or 0
            m.actual_consensus_reward += validator.actual_consensus_reward or 0

            m.missed_attestations += int(validator.missed_attestation == True)
            m.missed_consecutive_attestations += int(validator.previous_missed_attestation == True and validator.missed_attestation == True)

            m.proposed_blocks += validator.proposed_blocks_total
            m.missed_blocks += validator.missed_blocks_total
            m.proposed_finalized_blocks += validator.proposed_blocks_finalized_total
            m.missed_finalized_blocks += validator.missed_blocks_finalized_total

            m.future_blocks += validator.future_blocks_proposal

    return metrics


def compute_validator_metrics(validators: dict[int, WatchedValidator]) -> dict[str, AggregatedMetricsByLabel]:
    """Compute the metrics from a list of validators.

    Parameters:
    validators: list[WatchedValidator]

    Returns:
    dict[str, AggregatedMetricsByLabel]
    """
    metrics = defaultdict(AggregatedMetricsByLabel)

    with Pool() as p:
        v = validators.values()
        threads = []
        for batch in batched(v, int(len(v) / NB_THREADS)):
            threads.append(p.apply_async(_aggregate_validator_metrics, (batch, )))

        for thread in threads:
            entry = thread.get()
            logging.info(f'Aggregating results from a thread')
            for label, metric in entry.items():
                m = metrics[label]

                for status, count in metric.validator_status_count.items():
                    if status not in m.validator_status_count:
                        m.validator_status_count[status] = 0
                    m.validator_status_count[status] += count

                m.suboptimal_source_count += metric.suboptimal_source_count
                m.suboptimal_target_count += metric.suboptimal_target_count
                m.suboptimal_head_count += metric.suboptimal_head_count
                m.optimal_source_count += metric.optimal_source_count
                m.optimal_target_count += metric.optimal_target_count
                m.optimal_head_count += metric.optimal_head_count
                m.validator_slashes += metric.validator_slashes

                m.ideal_consensus_reward += metric.ideal_consensus_reward
                m.actual_consensus_reward += metric.actual_consensus_reward
                m.missed_attestations += metric.missed_attestations
                m.missed_consecutive_attestations += metric.missed_consecutive_attestations

                m.proposed_blocks += metric.proposed_blocks
                m.missed_blocks += metric.missed_blocks
                m.proposed_finalized_blocks += metric.proposed_finalized_blocks
                m.missed_finalized_blocks += metric.missed_finalized_blocks

                m.future_blocks += metric.future_blocks

    return metrics
                
                
def get_prometheus_metrics() -> PrometheusMetrics:
    """Get the Prometheus metrics.

    Returns:
    --------
    PrometheusMetrics
    """
    global _metrics

    if _metrics is None:
        _metrics = PrometheusMetrics(
            eth_slot=Gauge("eth_slot", "Current slot", ["network"]),
            eth_epoch=Gauge("eth_epoch", "Current epoch", ["network"]),
            eth_current_price_dollars=Gauge("eth_current_price_dollars", "Current price of ETH in USD", ["network"]),

            eth_validator_status_count=Gauge("eth_validator_status_count", "Validator status count sampled every epoch", ['scope', 'status', 'network']),
            eth_suboptimal_sources_rate=Gauge("eth_suboptimal_sources_rate", "Suboptimal sources rate sampled every epoch", ['scope', 'network']),
            eth_suboptimal_targets_rate=Gauge("eth_suboptimal_targets_rate", "Suboptimal targets rate sampled every epoch", ['scope', 'network']),
            eth_suboptimal_heads_rate=Gauge("eth_suboptimal_heads_rate", "Suboptimal heads rate sampled every epoch", ['scope', 'network']),
            eth_ideal_consensus_rewards_gwei=Gauge("eth_ideal_consensus_rewards_gwei", "Ideal consensus rewards sampled every epoch", ['scope', 'network']),
            eth_actual_consensus_rewards_gwei=Gauge("eth_actual_consensus_rewards_gwei", "Actual consensus rewards sampled every epoch", ['scope', 'network']),
            eth_consensus_rewards_rate=Gauge("eth_consensus_rewards_rate", "Consensus rewards rate sampled every epoch", ['scope', 'network']),
            eth_missed_attestations_count=Gauge("eth_missed_attestations", "Missed attestations in the last epoch", ['scope', 'network']),
            eth_missed_consecutive_attestations_count=Gauge("eth_missed_consecutive_attestations", "Missed consecutive attestations in the last two epochs", ['scope', 'network']),
            eth_slashed_validators_count=Gauge("eth_slashed_validators", "Slashed validators", ['scope', 'network']),

            eth_block_proposals_head_total=Counter("eth_block_proposals_head_total", "Total block proposals at head", ['scope', 'network']),
            eth_missed_block_proposals_head_total=Counter("eth_missed_block_proposals_head_total", "Total missed block proposals at head", ['scope', 'network']),
            eth_block_proposals_finalized_total=Counter("eth_block_proposals_finalized_total", "Total finalized block proposals", ['scope', 'network']),
            eth_missed_block_proposals_finalized_total=Counter("eth_missed_block_proposals_finalized_total", "Total missed finalized block proposals", ['scope', 'network']),
            eth_future_block_proposals=Gauge("eth_future_block_proposals", "Future block proposals", ['scope', 'network'])
        )

    return _metrics
