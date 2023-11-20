from eth_validator_watcher.exited_validators import (
    ExitedValidators,
    metric_our_exited_validators_count,
)
from eth_validator_watcher.models import Validators

Validator = Validators.DataItem.Validator


def test_process_exited_validators():
    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    our_exited_unslashed_index_to_validator = {
        44: Validator(pubkey="0x9012", effective_balance=32000000000, slashed=False),
        45: Validator(pubkey="0x3456", effective_balance=32000000000, slashed=False),
    }

    our_withdrawal_index_to_validator = {
        46: Validator(pubkey="0x1234", effective_balance=32000000000, slashed=False),
        47: Validator(pubkey="0x5678", effective_balance=32000000000, slashed=True),
    }

    exited_validators = ExitedValidators(slack)  # type: ignore

    exited_validators.process(
        our_exited_unslashed_index_to_validator, our_withdrawal_index_to_validator
    )

    assert metric_our_exited_validators_count.collect()[0].samples[0].value == 3  # type: ignore
    assert slack.counter == 0

    assert (
        exited_validators._ExitedValidators__our_exited_unslashed_indexes  # type: ignore
        == {44, 45}
    )

    our_exited_unslashed_index_to_validator = {
        44: Validator(pubkey="0x9012", effective_balance=32000000000, slashed=False),
        45: Validator(pubkey="0x3456", effective_balance=32000000000, slashed=False),
        48: Validator(pubkey="0x5432", effective_balance=32000000000, slashed=False),
    }
    exited_validators.process(
        our_exited_unslashed_index_to_validator, our_withdrawal_index_to_validator
    )

    assert metric_our_exited_validators_count.collect()[0].samples[0].value == 4  # type: ignore
    assert slack.counter == 1

    assert (
        exited_validators._ExitedValidators__our_exited_unslashed_indexes  # type: ignore
        == {44, 45, 48}
    )
