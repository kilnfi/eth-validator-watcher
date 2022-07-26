from eth_validator_watcher.utils import convert_hex_to_bools


def test_convert_hex_to_bools():
    expected = [
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        True,
        False,
        True,
        False,
    ]

    assert convert_hex_to_bools("0x0F0A") == expected
    assert convert_hex_to_bools("0F0A") == expected
