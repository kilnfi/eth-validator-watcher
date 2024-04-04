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

    eth_validator_status_count: Gauge
    eth_suboptimal_sources_rate: Gauge
    eth_suboptimal_targets_rate: Gauge
    eth_suboptimal_heads_rate: Gauge


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
            eth_validator_status_count=Gauge("eth_validator_status_count", "Validator status count", ['scope', 'status']),
            eth_suboptimal_sources_rate=Gauge("eth_suboptimal_sources_rate", "Suboptimal sources rate", ['scope']),
            eth_suboptimal_targets_rate=Gauge("eth_suboptimal_targets_rate", "Suboptimal targets rate", ['scope']),
            eth_suboptimal_heads_rate=Gauge("eth_suboptimal_heads_rate", "Suboptimal heads rate", ['scope']),
        )

    return _metrics
