import json
from pathlib import Path

import requests_mock
from eth_validator_watcher.suboptimal_attestations import aggregate_attestations
from tests.beacon import assets
from eth_validator_watcher.models import Block


def test_aggregate_attestations():
    beacon_url = "http://beacon:5052"
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
        block_dict = json.load(file_descriptor)

    block = Block(**block_dict)

    with requests_mock.Mocker() as mock:
        assert aggregate_attestations(block, 4839774) == expected
