from pathlib import Path

from eth_validator_watcher.utils import load_pubkeys_from_file
from tests.utils import assets


def test_load_pubkeys_from_file():
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"
    expected = {"0xaaa", "0xbbb", "0xccc"}
    assert load_pubkeys_from_file(pubkey_path) == expected
