import json
from pathlib import Path

from eth_validator_watcher.beacon import Beacon
from eth_validator_watcher.models import BeaconType
from pytest import raises
from requests import HTTPError, Response, codes
from requests_mock import Mocker
from tests.beacon import assets


def test_get_validators_liveness_lighthouse():
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
        beacon = Beacon(beacon_url, 90)
        expected = {42: True, 44: False, 46: True}

        assert (
            beacon.get_validators_liveness(
                beacon_type=BeaconType.LIGHTHOUSE,
                epoch=1664,
                validators_index={42, 44, 46},
            )
            == expected
        )


def test_get_validators_liveness_nimbus():
    beacon_url = "http://beacon:5052"
    beacon = Beacon(beacon_url, 90)

    assert beacon.get_validators_liveness(
        beacon_type=BeaconType.NIMBUS, epoch=1664, validators_index={42, 44, 46}
    ) == {42: True, 44: True, 46: True}


def test_get_validators_liveness_teku():
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
        beacon = Beacon(beacon_url, 90)
        expected = {42: True, 44: False, 46: True}

        assert (
            beacon.get_validators_liveness(
                beacon_type=BeaconType.OLD_TEKU,
                epoch=1664,
                validators_index={42, 44, 46},
            )
            == expected
        )


def test_get_validators_liveness_beacon_api():
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
        beacon = Beacon(beacon_url, 90)
        expected = {42: True, 44: False, 46: True}

        assert (
            beacon.get_validators_liveness(
                beacon_type=BeaconType.OTHER, epoch=1664, validators_index={42, 44, 46}
            )
            == expected
        )


def test_get_validators_liveness_beacon_api_bad_request():
    beacon_url = "http://beacon:5052"

    def post(url: str, **_) -> Response:
        assert url == f"{beacon_url}/eth/v1/validator/liveness/1664"
        response = Response()
        response.status_code = codes.bad_request

        return response

    beacon = Beacon(beacon_url, 90)
    beacon._Beacon__http_retry_not_found.post = post  # type: ignore

    expected = {42: True, 44: True, 46: True}

    assert expected == beacon.get_validators_liveness(
        beacon_type=BeaconType.OTHER, epoch=1664, validators_index={42, 44, 46}
    )


def test_get_validators_liveness_beacon_api_no_extended():
    beacon_url = "http://beacon:5052"

    def post(url: str, **_) -> Response:
        assert url == f"{beacon_url}/eth/v1/validator/liveness/1664"
        response = Response()
        response.status_code = codes.not_extended

        return response

    beacon = Beacon(beacon_url, 90)
    beacon._Beacon__http_retry_not_found.post = post  # type: ignore

    with raises(HTTPError):
        beacon.get_validators_liveness(
            beacon_type=BeaconType.OTHER, epoch=1664, validators_index={42, 44, 46}
        )
