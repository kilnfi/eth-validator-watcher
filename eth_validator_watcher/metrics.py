from dataclasses import dataclass

from prometheus_client import Counter, Gauge, Histogram


# This is global because Prometheus metrics don't support registration
# multiple times. This is a workaround for unit tests.
_metrics = None


@dataclass
class PrometheusMetrics:
    """Define the Prometheus metrics.
    """
    eth_slot: Gauge
    eth_epoch: Gauge
    eth_current_price: Gauge

    eth_validator_status_count: Gauge
    eth_suboptimal_sources_rate: Gauge
    eth_suboptimal_targets_rate: Gauge
    eth_suboptimal_heads_rate: Gauge
    eth_ideal_consensus_rewards: Gauge
    eth_actual_consensus_rewards: Gauge
    eth_consensus_rewards_rate: Gauge
    eth_missed_attestations: Gauge
    eth_missed_consecutive_attestations: Gauge


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
            eth_current_price=Gauge("eth_current_price", "Current price of ETH in USD"),
            eth_validator_status_count=Gauge("eth_validator_status_count", "Validator status count", ['scope', 'status']),
            eth_suboptimal_sources_rate=Gauge("eth_suboptimal_sources_rate", "Suboptimal sources rate", ['scope']),
            eth_suboptimal_targets_rate=Gauge("eth_suboptimal_targets_rate", "Suboptimal targets rate", ['scope']),
            eth_suboptimal_heads_rate=Gauge("eth_suboptimal_heads_rate", "Suboptimal heads rate", ['scope']),
            eth_ideal_consensus_rewards=Gauge("eth_ideal_consensus_rewards", "Ideal consensus rewards", ['scope']),
            eth_actual_consensus_rewards=Gauge("eth_actual_consensus_rewards", "Actual consensus rewards", ['scope']),
            eth_consensus_rewards_rate=Gauge("eth_consensus_rewards_rate", "Consensus rewards rate", ['scope']),
            eth_missed_attestations=Gauge("eth_missed_attestations", "Missed attestations in the last epoch", ['scope']),
            eth_missed_consecutive_attestations=Gauge("eth_missed_consecutive_attestations", "Missed consecutive attestations", ['scope']),
        )

    return _metrics
