import json
from pathlib import Path

import requests_mock
from eth_validator_watcher.beacon import Beacon
from tests.beacon import assets


def test_is_block_missed():
    beacon_url = "http://beacon:5052"
    slot = 4839775
    block_path = Path(assets.__file__).parent / "block.json"

    with block_path.open() as file_descriptor:
        block = json.load(file_descriptor)

    with requests_mock.Mocker() as mock:
        mock.get(f"{beacon_url}/eth/v2/beacon/blocks/{slot}", json=block)
        beacon = Beacon(beacon_url)

        assert not beacon.is_block_missed(slot)
