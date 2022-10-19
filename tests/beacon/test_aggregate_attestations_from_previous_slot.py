import json
from pathlib import Path

import requests_mock
from eth_validator_watcher.beacon import Beacon
from tests.beacon import assets


def test_aggregate_attestations_from_previous_slot():
    beacon_url = "http://beacon:5052"
    slot = 4839775
    block_path = Path(assets.__file__).parent / "block.json"

    expected = {
        1: [
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            # --
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            # --
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            # --
        ],
        2: [
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            # --
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            # --
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            # --
        ],
    }

    with block_path.open() as file_descriptor:
        block = json.load(file_descriptor)

    with requests_mock.Mocker() as mock:
        mock.get(f"{beacon_url}/eth/v2/beacon/blocks/{slot}", json=block)
        beacon = Beacon(beacon_url)

        assert beacon.aggregate_attestations_from_previous_slot(slot) == expected
