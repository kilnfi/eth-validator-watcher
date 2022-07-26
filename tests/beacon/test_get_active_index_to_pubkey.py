import json
from pathlib import Path

import requests_mock
from eth_validator_watcher.beacon import Beacon
from tests.beacon import assets


def test_get_active_index_to_pubkey():
    beacon_url = "http://beacon:5052"
    validators_path = Path(assets.__file__).parent / "validators_active.json"

    input = {
        "0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95",
        "0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c",
        "0xb2ff4716ed345b05dd1dfc6a5a9fa70856d8c75dcc9e881dd2f766d5f891326f0d10e96f3a444ce6c912b69c22c6754d",
        "0x8e323fd501233cd4d1b9d63d74076a38de50f2f584b001a5ac2412e4e46adb26d2fb2a6041e7e8c57cd4df0916729219",
    }

    expected = {
        0: "0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95",
        2: "0xb2ff4716ed345b05dd1dfc6a5a9fa70856d8c75dcc9e881dd2f766d5f891326f0d10e96f3a444ce6c912b69c22c6754d",
    }

    with validators_path.open() as file_descriptor:
        validators = json.load(file_descriptor)

    with requests_mock.Mocker() as mock:
        mock.get(
            f"{beacon_url}/eth/v1/beacon/states/head/validators?status=active",
            json=validators,
        )
        beacon = Beacon(beacon_url)

        assert beacon.get_active_index_to_pubkey(input) == expected
