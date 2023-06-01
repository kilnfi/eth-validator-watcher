import json
from pathlib import Path

from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon
from eth_validator_watcher.models import BeaconType
from tests.beacon import assets


def test_get_proposer_duties_lighthouse():
    beacon_url = "http://beacon:5052"

    liveness_request_path = (
        Path(assets.__file__).parent / "liveness_request_lighthouse.json"
    )

    liveness_response_path = Path(assets.__file__).parent / "liveness_response.json"

    with liveness_request_path.open() as file_descriptor:
        liveness_request = json.load(file_descriptor)

    with liveness_response_path.open() as file_descriptor:
        liveness_response = json.load(file_descriptor)

    def match_request(request) -> bool:
        return request.json() == liveness_request

    with Mocker() as mock:
        mock.post(
            f"{beacon_url}/lighthouse/liveness",
            additional_matcher=match_request,
            json=liveness_response,
        )
        beacon = Beacon(beacon_url)
        expected = {42: True, 44: False, 46: True}

        assert (
            beacon.get_validators_liveness(
                beacon_type=BeaconType.LIGHTHOUSE,
                epoch=1664,
                validators_index={42, 44, 46},
            )
            == expected
        )


def test_get_proposer_duties_teku():
    beacon_url = "http://beacon:5052"

    liveness_request_path = Path(assets.__file__).parent / "liveness_request_teku.json"
    liveness_response_path = Path(assets.__file__).parent / "liveness_response.json"

    with liveness_request_path.open() as file_descriptor:
        liveness_request = json.load(file_descriptor)

    with liveness_response_path.open() as file_descriptor:
        liveness_response = json.load(file_descriptor)

    def match_request(request) -> bool:
        return request.json() == liveness_request

    with Mocker() as mock:
        mock.post(
            f"{beacon_url}/eth/v1/validator/liveness/1664",
            additional_matcher=match_request,
            json=liveness_response,
        )
        beacon = Beacon(beacon_url)
        expected = {42: True, 44: False, 46: True}

        assert (
            beacon.get_validators_liveness(
                beacon_type=BeaconType.TEKU, epoch=1664, validators_index={42, 44, 46}
            )
            == expected
        )


def test_get_proposer_duties_beacon_api():
    beacon_url = "http://beacon:5052"

    liveness_request_path = (
        Path(assets.__file__).parent / "liveness_request_beacon_api.json"
    )

    liveness_response_path = Path(assets.__file__).parent / "liveness_response.json"

    with liveness_request_path.open() as file_descriptor:
        liveness_request = json.load(file_descriptor)

    with liveness_response_path.open() as file_descriptor:
        liveness_response = json.load(file_descriptor)

    def match_request(request) -> bool:
        return request.json() == liveness_request

    with Mocker() as mock:
        mock.post(
            f"{beacon_url}/eth/v1/validator/liveness/1664",
            additional_matcher=match_request,
            json=liveness_response,
        )
        beacon = Beacon(beacon_url)
        expected = {42: True, 44: False, 46: True}

        assert (
            beacon.get_validators_liveness(
                beacon_type=BeaconType.OTHER, epoch=1664, validators_index={42, 44, 46}
            )
            == expected
        )
