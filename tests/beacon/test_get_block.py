import json
from pathlib import Path

from pytest import raises
from requests import Response
from requests.exceptions import RetryError
from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon, NoBlockError
from tests.beacon import assets


def test_get_block_exists() -> None:
    block_path = Path(assets.__file__).parent / "block.json"

    with block_path.open() as file_descriptor:
        block_dict = json.load(file_descriptor)

    beacon = Beacon("http://beacon-node:5052")

    with Mocker() as mock:
        mock.get(
            f"http://beacon-node:5052/eth/v2/beacon/blocks/4839775", json=block_dict
        )
        block = beacon.get_block(4839775)
        assert block.data.message.proposer_index == 365100


def test_get_block_does_not_exist() -> None:
    def get(url: str, **_) -> Response:
        assert url == "http://beacon-node:5052/eth/v2/beacon/blocks/42"
        raise RetryError

    beacon = Beacon("http://beacon-node:5052")
    beacon._Beacon__http.get = get  # type: ignore

    with raises(NoBlockError):
        beacon.get_block(42)
