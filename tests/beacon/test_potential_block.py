from eth_validator_watcher.beacon import Beacon, NoBlockError
from eth_validator_watcher.models import Block


def test_get_block_exists() -> None:
    def get_block(slot: int) -> Block:
        assert slot == 42
        return "a fake block"  # type: ignore

    beacon = Beacon("http://beacon-node:5052")
    beacon.get_block = get_block  # type: ignore

    assert beacon.get_potential_block(42) == "a fake block"


def test_get_block_not_exists() -> None:
    def get_block(slot: int) -> Block:
        assert slot == 42
        raise NoBlockError

    beacon = Beacon("http://beacon-node:5052")
    beacon.get_block = get_block  # type: ignore

    assert beacon.get_potential_block(42) is None
