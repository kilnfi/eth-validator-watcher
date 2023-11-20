import json
from pathlib import Path

from pytest import fixture

from eth_validator_watcher.fee_recipient import (
    process_fee_recipient,
    metric_wrong_fee_recipient_proposed_block_count,
)
from eth_validator_watcher.models import Block, ExecutionBlock, Validators
from tests.fee_recipient import assets

Validator = Validators.DataItem.Validator


class Slack:
    def __init__(self):
        self.counter = 0

    def send_message(self, _: str) -> None:
        self.counter += 1


class Execution:
    def eth_get_block_by_hash(self, hash: str) -> ExecutionBlock:
        assert (
            hash == "0x9fc5b74ae5b8a0f7495314c7e6608e524c2ffe8581eca704208066cd922a1fee"
        )

        execution_block_path = Path(assets.__file__).parent / "execution_block.json"

        with execution_block_path.open() as file_descriptor:
            return ExecutionBlock(**json.load(file_descriptor))


class ExecutionEmptyBlock:
    def eth_get_block_by_hash(self, hash: str) -> ExecutionBlock:
        assert (
            hash == "0x9fc5b74ae5b8a0f7495314c7e6608e524c2ffe8581eca704208066cd922a1fee"
        )

        execution_block_path = (
            Path(assets.__file__).parent / "empty_execution_block.json"
        )

        with execution_block_path.open() as file_descriptor:
            return ExecutionBlock(**json.load(file_descriptor))


@fixture
def block() -> Block:
    block_file = Path(assets.__file__).parent / "block.json"
    with block_file.open() as file_descriptor:
        return Block(**json.load(file_descriptor))


def test_execution_is_none():
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block="A block",  # type: ignore
        index_to_validator={},
        execution=None,
        expected_fee_recipient="0x1234",
        slack=slack,  # type: ignore
    )

    counter_after = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore
    assert counter_after == counter_before

    assert slack.counter == 0


def test_fee_recipient_is_none():
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block="A block",  # type: ignore
        index_to_validator={},
        execution="execution",  # type: ignore
        expected_fee_recipient=None,
        slack=slack,  # type: ignore
    )

    assert slack.counter == 0


def test_not_our_validator(block: Block):
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block=block,
        index_to_validator={},
        execution="execution",  # type: ignore
        expected_fee_recipient="0x1234",
        slack=slack,  # type: ignore
    )

    counter_after = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore
    assert counter_after == counter_before

    assert slack.counter == 0


def test_our_validator_allright(block: Block):
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block=block,
        index_to_validator={
            365100: Validator(
                pubkey="0xabcd", effective_balance=32000000000, slashed=False
            )
        },
        execution="execution",  # type: ignore
        expected_fee_recipient="0xebec795c9c8bbd61ffc14a6662944748f299cacf",
        slack=slack,  # type: ignore
    )

    counter_after = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore
    assert counter_after == counter_before

    assert slack.counter == 0


def test_our_validator_ok_in_last_tx(block: Block):
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block=block,
        index_to_validator={
            365100: Validator(
                pubkey="0xabcd", effective_balance=32000000000, slashed=False
            )
        },
        execution=Execution(),  # type: ignore
        expected_fee_recipient="0x760a6314a1d207377271917075f88e520141d55f",
        slack=slack,  # type: ignore
    )

    counter_after = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore
    assert counter_after == counter_before

    assert slack.counter == 0


def test_our_validator_not_ok_empty_block(block: Block):
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block=block,
        index_to_validator={
            365100: Validator(
                pubkey="0xabcd", effective_balance=32000000000, slashed=False
            )
        },
        execution=ExecutionEmptyBlock(),  # type: ignore
        expected_fee_recipient="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        slack=slack,  # type: ignore
    )

    counter_after = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore
    assert counter_after == counter_before + 1

    assert slack.counter == 1


def test_our_validator_not_ok(block: Block):
    slack = Slack()
    counter_before = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore

    process_fee_recipient(
        block=block,
        index_to_validator={
            365100: Validator(
                pubkey="0xabcd", effective_balance=32000000000, slashed=False
            )
        },
        execution=Execution(),  # type: ignore
        expected_fee_recipient="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        slack=slack,  # type: ignore
    )

    counter_after = metric_wrong_fee_recipient_proposed_block_count.collect()[0].samples[0].value  # type: ignore
    assert counter_after == counter_before + 1

    assert slack.counter == 1
