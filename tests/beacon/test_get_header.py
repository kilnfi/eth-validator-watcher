import json
from pathlib import Path

from pytest import raises
from requests import HTTPError, Response, codes, exceptions
from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon, NoBlockError
from eth_validator_watcher.models import BlockIdentierType, Header
from tests.beacon import assets


def test_get_header_exists() -> None:
    block_path = Path(assets.__file__).parent / "header.json"

    with block_path.open() as file_descriptor:
        header_dict = json.load(file_descriptor)

    beacon = Beacon("http://beacon-node:5052", 90)

    for identifier, value in {
        "head": BlockIdentierType.HEAD,
        "genesis": BlockIdentierType.GENESIS,
        "finalized": BlockIdentierType.FINALIZED,
        7523776: 7523776,
    }.items():
        with Mocker() as mock:
            mock.get(
                f"http://beacon-node:5052/eth/v1/beacon/headers/{identifier}",
                json=header_dict,
            )
            header = beacon.get_header(value)

        assert header.data.header.message.slot == 7523776


def test_get_header_does_not_exist() -> None:
    def get(url: str, **_) -> Response:
        assert url == "http://beacon-node:5052/eth/v1/beacon/headers/42"
        response = Response()
        response.status_code = codes.NOT_FOUND

        raise HTTPError(response=response)

    beacon = Beacon("http://beacon-node:5052", 90)
    beacon._Beacon__http.get = get  # type: ignore

    with raises(NoBlockError):
        beacon.get_header(42)


def test_get_header_invalid_query() -> None:
    def get(url: str, **_) -> Response:
        assert url == "http://beacon-node:5052/eth/v1/beacon/headers/-42"
        response = Response()
        response.status_code = codes.INTERNAL_SERVER_ERROR

        raise HTTPError(response=response)

    beacon = Beacon("http://beacon-node:5052", 90)
    beacon._Beacon__http.get = get  # type: ignore

    with raises(exceptions.RequestException):
        beacon.get_header(-42)
