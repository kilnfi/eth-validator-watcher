import logging
import os

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import batched

from prometheus_client import Counter, Gauge

from eth_validator_watcher_ext import fast_compute_validator_metrics, MetricsByLabel

from .utils import LABEL_SCOPE_WATCHED
from .watched_validators import WatchedValidator


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


def compute_validator_metrics(validators: dict[int, WatchedValidator], slot: int) -> dict[str, MetricsByLabel]:
    """Compute the metrics from a list of validators.

    Parameters:
    validators: list[WatchedValidator]

    Returns:
    dict[str, MetricsByLabel]
    """
    logging.info(f"📊 Computing metrics for {len(validators)} validators")
    metrics = fast_compute_validator_metrics(validators)
    
    for _, v in validators.items():
        v.reset_blocks()

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
