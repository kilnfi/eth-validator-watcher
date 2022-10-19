from eth_validator_watcher.utils import apply_mask


def test_apply_mask():
    input = ["a", "b", "c", "d", "e"]
    mask = [True, False, False, True, False]
    expected = {"a", "d"}

    assert apply_mask(input, mask) == expected
