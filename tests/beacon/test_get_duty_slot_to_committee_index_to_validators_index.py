import json
from pathlib import Path

import requests_mock

from eth_validator_watcher.beacon import Beacon
from tests.beacon import assets


def test_get_duty_slot_to_committee_index_to_validators_index():
    beacon_url = "http://beacon:5052"
    epoch = 154000
    committees_path = Path(assets.__file__).parent / "committees.json"

    expected = {
        4928000: {0: [1, 2, 3], 1: [4, 5, 6]},
        4928001: {0: [7, 8, 9], 1: [10, 11, 12]},
    }

    with committees_path.open() as file_descriptor:
        committees = json.load(file_descriptor)

    with requests_mock.Mocker() as mock:
        mock.get(
            f"{beacon_url}/eth/v1/beacon/states/head/committees?epoch={epoch}",
            json=committees,
        )

        beacon = Beacon(beacon_url, 90)

        assert (
            beacon.get_duty_slot_to_committee_index_to_validators_index(epoch)
            == expected
        )
