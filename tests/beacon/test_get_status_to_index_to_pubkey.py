import json
from eth_validator_watcher.beacon import Beacon
from tests.beacon import assets
from pathlib import Path
from requests_mock import Mocker
from eth_validator_watcher.models import Validators

StatusEnum = Validators.DataItem.StatusEnum


def test_get_status_to_index_to_pubkey() -> None:
    asset_path = Path(assets.__file__).parent / "validators.json"

    with asset_path.open() as file_descriptor:
        validators = json.load(file_descriptor)

    beacon = Beacon("http://localhost:5052")
    expected = {
        StatusEnum.activeOngoing: {
            0: "0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95",
            4: "0xa62420543ceef8d77e065c70da15f7b731e56db5457571c465f025e032bbcd263a0990c8749b4ca6ff20d77004454b51",
        },
        StatusEnum.pendingQueued: {
            1: "0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c",
        },
        StatusEnum.activeExiting: {
            2: "0xb2ff4716ed345b05dd1dfc6a5a9fa70856d8c75dcc9e881dd2f766d5f891326f0d10e96f3a444ce6c912b69c22c6754d",
        },
        StatusEnum.exitedSlashed: {
            3: "0x8e323fd501233cd4d1b9d63d74076a38de50f2f584b001a5ac2412e4e46adb26d2fb2a6041e7e8c57cd4df0916729219"
        },
    }

    with Mocker() as mock:
        mock.get(
            "http://localhost:5052/eth/v1/beacon/states/head/validators?status=pending_queued&status=active&status=exited_slashed",
            json=validators,
        )

        actual = beacon.get_status_to_index_to_pubkey()

    assert expected == actual
