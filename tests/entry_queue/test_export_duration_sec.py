from eth_validator_watcher.entry_queue import (
    metric_entry_queue_duration_sec,
    export_duration_sec,
)


def test_export_duration_sec() -> None:
    export_duration_sec(0, 8)
    assert metric_entry_queue_duration_sec.collect()[0].samples[0].value == 768  # type: ignore
