from eth_validator_watcher.utils import convert_seconds_to_dhms


def test_convert_secondes_to_dhms() -> None:
    assert convert_seconds_to_dhms(0) == (0, 0, 0, 0)
    assert convert_seconds_to_dhms(61) == (0, 0, 1, 1)
    assert convert_seconds_to_dhms(3601) == (0, 1, 0, 1)
    assert convert_seconds_to_dhms(86462) == (1, 0, 1, 2)
