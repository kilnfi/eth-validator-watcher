import pytest
from eth_validator_watcher.utils import remove_all_items_from_last_true


def test_remove_all_items_from_last_true():
    input = [False, True, False, True, True, False]
    expected = [False, True, False, True]
    assert remove_all_items_from_last_true(input) == expected

    input = [True] * 5
    expected = [True] * 4
    assert remove_all_items_from_last_true(input) == expected

    with pytest.raises(StopIteration):
        remove_all_items_from_last_true([False, False])
