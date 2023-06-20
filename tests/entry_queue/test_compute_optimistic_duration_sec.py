from eth_validator_watcher.entry_queue import (
    NB_SECONDS_PER_EPOCH,
    compute_optimistic_duration_sec,
)


def test_compute_optimistic_duration_sec_buckets_differ() -> None:
    assert (
        compute_optimistic_duration_sec(327_678, 589_826 - 327_678)
        == (2 // 4 + 65536 // 5 + 65536 // 6 + 65536 // 7 + 65536 // 8 + 3 // 9)
        * NB_SECONDS_PER_EPOCH
    )


def test_compute_optimistic_duration_sec_buckets_same() -> None:
    assert compute_optimistic_duration_sec(4, 9) == 2 * NB_SECONDS_PER_EPOCH
