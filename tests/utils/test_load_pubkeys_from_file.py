from pathlib import Path

from eth_validator_watcher.utils import load_validator_data_from_file
from tests.utils import assets


def test_load_validator_data_from_file():
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"
    print(pubkey_path)
    expected = {
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": ("teku.0", "eth-holesky02"),
            "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": ("teku.0", "eth-holesky02"),
        }
    assert load_validator_data_from_file(pubkey_path) == expected
