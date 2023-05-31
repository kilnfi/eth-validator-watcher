import json
from pathlib import Path

import requests_mock

from eth_validator_watcher.beacon import Beacon
from eth_validator_watcher.models import Genesis
from tests.beacon import assets


def test_get_pending_index_to_pubkey():
    beacon_url = "http://beacon:5052"
    genesis_path = Path(assets.__file__).parent / "genesis.json"

    with genesis_path.open() as file_descriptor:
        genesis = json.load(file_descriptor)

    expected = Genesis(
        data=Genesis.Data(
            genesis_time=1590832934,
            genesis_validators_root="0xcf8e0d4e9587369b2301d0790347320302cc0943d5a1884560367e8208d920f2",
            genesis_fork_version="0x00000000",
        )
    )

    with requests_mock.Mocker() as mock:
        mock.get(
            f"{beacon_url}/eth/v1/beacon/genesis",
            json=genesis,
        )
        beacon = Beacon(beacon_url)

        assert beacon.get_genesis() == expected
