from pathlib import Path

from eth_validator_watcher.utils import get_our_pubkeys
from tests.utils import assets


def test_get_our_pubkeys() -> None:
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"
    expected = {
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": ("teku.0", "eth-holesky02"),
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": ("teku.0", "eth-holesky02"),
    }
    assert get_our_pubkeys(pubkey_path) == expected  # type: ignore
