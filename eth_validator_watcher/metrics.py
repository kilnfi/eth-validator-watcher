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
            eth_validator_status_count=Gauge("eth_validator_status_count", "Validator status count", ['scope', 'status'])
        )

    return _metrics
