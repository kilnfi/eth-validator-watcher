from eth_validator_watcher.utils import is_eth1_address


def test_is_eth1_address() -> None:
    # No `0x` prefix
    assert not is_eth1_address("e688b84b23f322a994a53dbf8e15fa82cdb71127")

    # Too short
    assert not is_eth1_address("0xe688b84b23f322a994a")

    # Too long
    assert not is_eth1_address(
        "0xe688b84b23f322a994ae688b84b23f322a994ae688b84b23f322a994a"
    )

    # OK
    assert is_eth1_address("0xe688b84b23f322a994a53dbf8e15fa82cdb71127")
