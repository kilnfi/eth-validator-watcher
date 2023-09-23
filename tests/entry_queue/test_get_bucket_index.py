from pytest import raises

from eth_validator_watcher.entry_queue import get_bucket_index


def test_get_bucket_index_nominal() -> None:
    assert get_bucket_index(0) == 0
    assert get_bucket_index(327_679) == 0
    assert get_bucket_index(327_680) == 1
    assert get_bucket_index(1_310_719) == 15


def test_get_bucket_index_raise() -> None:
    with raises(RuntimeError):
        get_bucket_index(3_000_000)
