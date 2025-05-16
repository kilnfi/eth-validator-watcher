import logging

from dataclasses import dataclass

from prometheus_client import Counter, Gauge

from eth_validator_watcher_ext import fast_compute_validator_metrics, MetricsByLabel

from .watched_validators import WatchedValidator


# This is global because Prometheus metrics don't support registration
# multiple times. This is a workaround for unit tests.
_metrics = None


@dataclass
class PrometheusMetrics:
    """Define the Prometheus metrics for validator monitoring.

    We sometimes have two declinations of the same metric, one for the
    base validator, and one for the stake-scaled validator. Example:

    eth_validator_status_count (base validator metric, absolute)
    eth_validator_status_scaled_count (stake-scaled validator metric, relative)

    Args:
        None

    Returns:
        None
    """
    eth_slot: Gauge
    eth_epoch: Gauge
    eth_current_price_dollars: Gauge

    # Queues
    eth_pending_deposits_count: Gauge
    eth_pending_deposits_value: Gauge
    eth_pending_consolidations_count: Gauge
    eth_pending_withdrawals_count: Gauge

    # The scaled version is multiplied by EB/32.
    eth_validator_status_count: Gauge
    eth_validator_status_scaled_count: Gauge
    eth_validator_type_count: Gauge
    eth_validator_type_scaled_count: Gauge

    # Those are already stake-scaled
    eth_suboptimal_sources_rate: Gauge
    eth_suboptimal_targets_rate: Gauge
    eth_suboptimal_heads_rate: Gauge
    eth_consensus_rewards_rate: Gauge
    eth_ideal_consensus_rewards_gwei: Gauge
    eth_actual_consensus_rewards_gwei: Gauge

    # The scaled version is multiplied by EB/32.
    eth_missed_attestations_count: Gauge
    eth_missed_attestations_scaled_count: Gauge
    eth_missed_consecutive_attestations_count: Gauge
    eth_missed_consecutive_attestations_scaled_count: Gauge
    eth_slashed_validators_count: Gauge
    eth_missed_duties_at_slot_count: Gauge
    eth_missed_duties_at_slot_scaled_count: Gauge
    eth_performed_duties_at_slot_count: Gauge
    eth_performed_duties_at_slot_scaled_count: Gauge
    eth_duties_rate: Gauge
    eth_duties_rate_scaled: Gauge

    # Those are already stake-scaled
    eth_block_proposals_head_total: Counter
    eth_missed_block_proposals_head_total: Counter
    eth_block_proposals_finalized_total: Counter
    eth_missed_block_proposals_finalized_total: Counter

    eth_future_block_proposals: Gauge


def compute_validator_metrics(validators: dict[int, WatchedValidator], slot: int) -> dict[str, MetricsByLabel]:
    """Compute the metrics from a dictionary of validators.

    Args:
        validators: dict[int, WatchedValidator]
            Dictionary of validator index to WatchedValidator objects.
        slot: int
            Current slot being processed.

    Returns:
        dict[str, MetricsByLabel]
            Dictionary of metric names to computed metrics by label.
    """
    logging.info(f"📊 Computing metrics for {len(validators)} validators")
    metrics = fast_compute_validator_metrics(validators, slot)

    for _, v in validators.items():
        v.reset_blocks()

    return metrics


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get or initialize the Prometheus metrics singleton.

    Args:
        None

    Returns:
        PrometheusMetrics
            The Prometheus metrics singleton instance.
    """
    global _metrics

    if _metrics is None:
        _metrics = PrometheusMetrics(
            eth_slot=Gauge("eth_slot", "Current slot", ["network"]),
            eth_epoch=Gauge("eth_epoch", "Current epoch", ["network"]),
            eth_current_price_dollars=Gauge("eth_current_price_dollars", "Current price of ETH in USD", ["network"]),

            eth_pending_deposits_count=Gauge("eth_pending_deposits_count", "Pending deposits count sampled every epoch", ['network']),
            eth_pending_deposits_value=Gauge("eth_pending_deposits_value", "Pending deposits value sampled every epoch", ['network']),
            eth_pending_consolidations_count=Gauge("eth_pending_consolidations_count", "Pending consolidations count sampled every epoch", ['network']),
            eth_pending_withdrawals_count=Gauge("eth_pending_withdrawals_count", "Pending withdrawals count sampled every epoch", ['network']),

            eth_validator_status_count=Gauge("eth_validator_status_count", "Validator status count sampled every epoch", ['scope', 'status', 'network']),
            eth_validator_status_scaled_count=Gauge("eth_validator_status_scaled_count", "Stake-scaled validator status count sampled every epoch", ['scope', 'status', 'network']),
            eth_validator_type_count=Gauge("eth_validator_type_count", "Validator type count sampled every epoch", ['scope', 'type', 'network']),
            eth_validator_type_scaled_count=Gauge("eth_validator_type_scaled_count", "Stake-scaled validator type count sampled every epoch", ['scope', 'type', 'network']),
            eth_suboptimal_sources_rate=Gauge("eth_suboptimal_sources_rate", "Suboptimal sources rate sampled every epoch", ['scope', 'network']),
            eth_suboptimal_targets_rate=Gauge("eth_suboptimal_targets_rate", "Suboptimal targets rate sampled every epoch", ['scope', 'network']),
            eth_suboptimal_heads_rate=Gauge("eth_suboptimal_heads_rate", "Suboptimal heads rate sampled every epoch", ['scope', 'network']),
            eth_ideal_consensus_rewards_gwei=Gauge("eth_ideal_consensus_rewards_gwei", "Ideal consensus rewards sampled every epoch", ['scope', 'network']),
            eth_actual_consensus_rewards_gwei=Gauge("eth_actual_consensus_rewards_gwei", "Actual consensus rewards sampled every epoch", ['scope', 'network']),
            eth_consensus_rewards_rate=Gauge("eth_consensus_rewards_rate", "Consensus rewards rate sampled every epoch", ['scope', 'network']),
            eth_missed_attestations_count=Gauge("eth_missed_attestations", "Missed attestations in the last epoch", ['scope', 'network']),
            eth_missed_attestations_scaled_count=Gauge("eth_missed_attestations_scaled", "Stake-scaled missed attestations in the last epoch", ['scope', 'network']),
            eth_missed_consecutive_attestations_count=Gauge("eth_missed_consecutive_attestations", "Missed consecutive attestations in the last two epochs", ['scope', 'network']),
            eth_missed_consecutive_attestations_scaled_count=Gauge("eth_missed_consecutive_attestations_scaled", "Stake-scaled missed consecutive attestations in the last two epochs", ['scope', 'network']),
            eth_slashed_validators_count=Gauge("eth_slashed_validators", "Slashed validators", ['scope', 'network']),
            eth_missed_duties_at_slot_count=Gauge("eth_missed_duties_at_slot", "Missed validator duties in last slot", ['scope', 'network']),
            eth_missed_duties_at_slot_scaled_count=Gauge("eth_missed_duties_at_slot_scaled", "Stake-scaled missed validator duties in last slot", ['scope', 'network']),
            eth_performed_duties_at_slot_count=Gauge("eth_performed_duties_at_slot", "Performed validator duties in last slot", ['scope', 'network']),
            eth_performed_duties_at_slot_scaled_count=Gauge("eth_performed_duties_at_slot_scaled", "Stake-scaled performed validator duties in last slot", ['scope', 'network']),
            eth_duties_rate=Gauge("eth_duties_rate", "Duties rate in last slot", ['scope', 'network']),
            eth_duties_rate_scaled=Gauge("eth_duties_rate_scaled", "Stake-scaled duties rate in last slot", ['scope', 'network']),
            eth_block_proposals_head_total=Counter("eth_block_proposals_head_total", "Total block proposals at head", ['scope', 'network']),
            eth_missed_block_proposals_head_total=Counter("eth_missed_block_proposals_head_total", "Total missed block proposals at head", ['scope', 'network']),
            eth_block_proposals_finalized_total=Counter("eth_block_proposals_finalized_total", "Total finalized block proposals", ['scope', 'network']),
            eth_missed_block_proposals_finalized_total=Counter("eth_missed_block_proposals_finalized_total", "Total missed finalized block proposals", ['scope', 'network']),
            eth_future_block_proposals=Gauge("eth_future_block_proposals", "Future block proposals", ['scope', 'network'])
        )

    return _metrics
