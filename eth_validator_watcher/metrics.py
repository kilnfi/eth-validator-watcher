from dataclasses import dataclass

from prometheus_client import Gauge


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

    # We use Gauge here while we should use a counter semantically,
    # but it is not possible to explictly set a counter value in
    # Prometheus' API (to prevent decreasing it). We use the _total
    # terminology to make it clear that it is a counter.
    
    eth_block_proposals_head_total: Gauge
    eth_missed_block_proposals_head_total: Gauge
    eth_block_proposals_finalized_total: Gauge
    eth_missed_block_proposals_finalized_total: Gauge


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get the Prometheus metrics.

    Returns:
    --------
    PrometheusMetrics
    """
    global _metrics

    if _metrics is None:
        _metrics = PrometheusMetrics(
            eth_slot=Gauge("eth_slot", "Current slot"),
            eth_epoch=Gauge("eth_epoch", "Current epoch"),
            eth_current_price_dollars=Gauge("eth_current_price_dollars", "Current price of ETH in USD"),

            eth_validator_status_count=Gauge("eth_validator_status_count", "Validator status count sampled every epoch", ['scope', 'status']),
            eth_suboptimal_sources_rate=Gauge("eth_suboptimal_sources_rate", "Suboptimal sources rate sampled every epoch", ['scope']),
            eth_suboptimal_targets_rate=Gauge("eth_suboptimal_targets_rate", "Suboptimal targets rate sampled every epoch", ['scope']),
            eth_suboptimal_heads_rate=Gauge("eth_suboptimal_heads_rate", "Suboptimal heads rate sampled every epoch", ['scope']),
            eth_ideal_consensus_rewards_gwei=Gauge("eth_ideal_consensus_rewards_gwei", "Ideal consensus rewards sampled every epoch", ['scope']),
            eth_actual_consensus_rewards_gwei=Gauge("eth_actual_consensus_rewards_gwei", "Actual consensus rewards sampled every epoch", ['scope']),
            eth_consensus_rewards_rate=Gauge("eth_consensus_rewards_rate", "Consensus rewards rate sampled every epoch", ['scope']),
            eth_missed_attestations_count=Gauge("eth_missed_attestations", "Missed attestations in the last epoch", ['scope']),
            eth_missed_consecutive_attestations_count=Gauge("eth_missed_consecutive_attestations", "Missed consecutive attestations in the last two epochs", ['scope']),

            eth_block_proposals_head_total=Gauge("eth_block_proposals_head_total", "Total block proposals at head", ['scope']),
            eth_missed_block_proposals_head_total=Gauge("eth_missed_block_proposals_head_total", "Total missed block proposals at head", ['scope']),
            eth_block_proposals_finalized_total=Gauge("eth_block_proposals_finalized_total", "Total finalized block proposals", ['scope']),
            eth_missed_block_proposals_finalized_total=Gauge("eth_missed_block_proposals_finalized_total", "Total missed finalized block proposals", ['scope']),
        )

    return _metrics
