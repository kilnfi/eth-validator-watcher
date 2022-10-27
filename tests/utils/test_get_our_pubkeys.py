from pathlib import Path

from eth_validator_watcher.utils import get_our_pubkeys
from tests.utils import assets


class Web3Signer:
    @staticmethod
    def load_pubkeys() -> set[str]:
        return {"0xccc", "0xddd", "0xeee"}


def test_get_our_pubkeys_not_epoch_start():
    web3signer = Web3Signer()
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"

    our_pubkeys = {"0xaaa", "0xbbb"}
    expected = our_pubkeys
    assert get_our_pubkeys(pubkey_path, {web3signer}, our_pubkeys, 2) == expected


def test_get_our_pubkeys_first_call():
    web3signer = Web3Signer()
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"

    our_pubkeys = None
    expected = {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}
    assert get_our_pubkeys(pubkey_path, {web3signer}, our_pubkeys, 2) == expected


def test_get_our_pubkeys_epoch_start():
    web3signer = Web3Signer()
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"

    our_pubkeys = {"0xaaa", "0xbbb"}
    expected = {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}
    assert get_our_pubkeys(pubkey_path, {web3signer}, our_pubkeys, 32) == expected
