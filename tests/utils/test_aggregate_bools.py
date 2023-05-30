import pytest

from eth_validator_watcher.utils import aggregate_bools


def test_aggregate_bools():
    input = [[False, False, True], [False, True, False]]
    expected = [False, True, True]

    assert aggregate_bools(input) == expected

    input = [[False, False], [False, True, False]]

    with pytest.raises(ValueError):
        aggregate_bools(input)
