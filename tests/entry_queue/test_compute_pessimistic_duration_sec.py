from eth_validator_watcher.entry_queue import (
    compute_pessimistic_duration_sec,
    NB_SECONDS_PER_EPOCH,
)


def test_compute_pessimistic_duration_sec() -> None:
    assert compute_pessimistic_duration_sec(42_000, 0) == 0
    assert compute_pessimistic_duration_sec(42_000, 3) == 0
    assert compute_pessimistic_duration_sec(42_000, 4) == NB_SECONDS_PER_EPOCH
    assert compute_pessimistic_duration_sec(42_000, 5) == NB_SECONDS_PER_EPOCH

    assert (
        compute_pessimistic_duration_sec(678_000, 100_000)
        == (100_000 // 10) * NB_SECONDS_PER_EPOCH
    )
