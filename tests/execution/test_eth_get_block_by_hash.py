import json
from pathlib import Path

from requests_mock import Mocker

from eth_validator_watcher.execution import Execution
from eth_validator_watcher.models import ExecutionBlock
from tests.execution import assets


def test_eth_get_block_by_hash() -> None:
    execution = Execution("http://execution:8545")
    execution_block_path = Path(assets.__file__).parent / "block.json"

    with execution_block_path.open() as file_descriptor:
        execution_block_dict = json.load(file_descriptor)

    def match_request(request) -> bool:
        return request.json() == dict(
            jsonrpc="2.0",
            method="eth_getBlockByHash",
            params=[
                "0x963239e3b325016690703704b95d8ed8ab58d268eb31654d48b278e187ff6771",
                True,
            ],
            id="1",
        )

    expected = ExecutionBlock(
        jsonrpc="2.0",
        id=1,
        result=ExecutionBlock.Result(
            transactions=[
                ExecutionBlock.Result.Transaction(
                    to="0x760a6314a1d207377271917075f88e520141d55e"
                ),
                ExecutionBlock.Result.Transaction(
                    to="0x760a6314a1d207377271917075f88e520141d55f"
                ),
            ]
        ),
    )

    with Mocker() as mock:
        mock.post(
            f"http://execution:8545",
            json=execution_block_dict,
            additional_matcher=match_request,
        )

        actual = execution.eth_get_block_by_hash(
            "0x963239e3b325016690703704b95d8ed8ab58d268eb31654d48b278e187ff6771"
        )

    assert actual == expected
