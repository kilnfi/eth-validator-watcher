from eth_validator_watcher.utils import switch_endianness


def test_switch_endianness():
    input = [
        False,
        False,
        True,
        False,
        True,
        True,
        True,
        False,
        True,
        False,
        True,
        False,
        False,
        True,
        True,
        True,
    ]

    expected = [
        False,
        True,
        True,
        True,
        False,
        True,
        False,
        False,
        True,
        True,
        True,
        False,
        False,
        True,
        False,
        True,
    ]

    assert switch_endianness(input) == expected
