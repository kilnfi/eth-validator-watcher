from pytest import raises

from eth_validator_watcher.utils import eth1_address_0x_prefixed


def test_eth1_address_0x_prefixed_invalid() -> None:
    # Too short
    with raises(ValueError):
        eth1_address_0x_prefixed("0x123")

    # Too long
    with raises(ValueError):
        eth1_address_0x_prefixed(
            "0x123456789012345678901234567890123456789012345678901234567890123"
        )

    # Invalid character
    with raises(ValueError):
        eth1_address_0x_prefixed("0x8d8b1b85d02d05ad3a14e2e9cc7b458d5invalid")


def test_eth1_address_0x_prefixed_valid_already_prefixed() -> None:
    address = "0x8d8b1b85d02d05ad3a14e2e9cc7b458d5c7d8f8c"
    assert eth1_address_0x_prefixed(address) == address


def test_eth1_address_0x_prefixed_valid_not_already_prefixed() -> None:
    address_without_prefix = "8d8b1b85d02d05ad3a14e2e9cc7b458d5c7d8f8c"
    address_with_prefix = "0x8d8b1b85d02d05ad3a14e2e9cc7b458d5c7d8f8c"
    assert eth1_address_0x_prefixed(address_without_prefix) == address_with_prefix
