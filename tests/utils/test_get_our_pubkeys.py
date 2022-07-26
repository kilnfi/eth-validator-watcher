from pathlib import Path
from eth_validator_watcher.utils import get_our_pubkeys
from tests.utils import assets


class Web3Signer:
    @staticmethod
    def load_pubkeys() -> set[str]:
        return {"0xccc", "0xddd", "0xeee"}


def test_get_our_pubkeys() -> None:
    pubkey_path = Path(assets.__file__).parent / "pubkeys.txt"
    web3signer = Web3Signer()

    expected = {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}
    assert get_our_pubkeys(pubkey_path, web3signer) == expected  # type: ignore
