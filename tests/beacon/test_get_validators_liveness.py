import json
from pathlib import Path

from requests_mock import Mocker
from eth_validator_watcher.beacon import Beacon

from tests.beacon import assets


def test_get_proposer_duties():
    beacon_url = "http://beacon:5052"

    liveness_request_path = Path(assets.__file__).parent / "liveness_request.json"
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

        assert beacon.get_validators_liveness(1664, {42, 44, 46}) == expected
