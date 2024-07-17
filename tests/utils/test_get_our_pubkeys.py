from pathlib import Path

from eth_validator_watcher.models import KeyReporterQueryResponse
from eth_validator_watcher.utils import (
    get_our_pubkeys,
    load_validator_data_from_key_reporter,
)
from tests.utils import assets
import requests_mock


def test_get_our_pubkeys() -> None:
    pubkey_url = "http://key-reporter.net:43000/ethereum"
    mock_response: KeyReporterQueryResponse = {
        "validators": [
            {
                "validator_public_key": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "validator_id": "eth-holesky02",
                "deployment_id": "teku.0",
            },
            {
                "validator_public_key": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "validator_id": "eth-holesky02",
                "deployment_id": "teku.0",
            },
        ]
    }
    expected = {
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": (
            "teku.0",
            "eth-holesky02",
        ),
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": (
            "teku.0",
            "eth-holesky02",
        ),
    }
    with requests_mock.Mocker() as mock:
        mock.post(f"{pubkey_url}", json=mock_response)
        assert load_validator_data_from_key_reporter(pubkey_url) == expected
        assert get_our_pubkeys(pubkey_url) == expected  # type: ignore
