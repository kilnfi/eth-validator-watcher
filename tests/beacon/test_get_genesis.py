import json
from pathlib import Path

import requests_mock

from eth_validator_watcher.beacon import Beacon
from eth_validator_watcher.models import Genesis
from tests.beacon import assets


def test_get_genesis():
    beacon_url = "http://beacon:5052"
    genesis_path = Path(assets.__file__).parent / "genesis.json"

    with genesis_path.open() as file_descriptor:
        genesis = json.load(file_descriptor)

    expected = Genesis(
        data=Genesis.Data(
            genesis_time=1590832934,
        )
    )

    with requests_mock.Mocker() as mock:
        mock.get(
            f"{beacon_url}/eth/v1/beacon/genesis",
            json=genesis,
        )
        beacon = Beacon(beacon_url, 90)

        assert beacon.get_genesis() == expected
