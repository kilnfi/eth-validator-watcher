from pytest import raises

from eth_validator_watcher.utils import eth1_address_lower_0x_prefixed


def test_eth1_address_0x_prefixed_invalid() -> None:
    # Too short
    with raises(ValueError):
        eth1_address_lower_0x_prefixed("0x123")

    # Too long
    with raises(ValueError):
        eth1_address_lower_0x_prefixed(
            "0x123456789012345678901234567890123456789012345678901234567890123"
        )

    # Invalid character
    with raises(ValueError):
        eth1_address_lower_0x_prefixed("0x8d8b1b85d02d05ad3a14e2e9cc7b458d5invalid")


def test_eth1_address_0x_prefixed_valid_already_prefixed() -> None:
    input = "0x8D8B1b85D02d05Ad3a14E2e9cC7b458d5c7d8f8c"
    expected_output = "0x8d8b1b85d02d05ad3a14e2e9cc7b458d5c7d8f8c"
    assert eth1_address_lower_0x_prefixed(input) == expected_output


def test_eth1_address_0x_prefixed_valid_not_already_prefixed() -> None:
    input = "8D8B1b85D02d05Ad3a14E2e9cC7b458d5c7d8f8c"
    expected_output = "0x8d8b1b85d02d05ad3a14e2e9cc7b458d5c7d8f8c"
    assert eth1_address_lower_0x_prefixed(input) == expected_output
