from eth_validator_watcher.slashed_validators import (
    SlashedValidators,
    our_exited_slashed_validators_count,
    total_exited_slashed_validators_count,
)

from eth_validator_watcher.models import Validators

Validator = Validators.DataItem.Validator


def test_process_slashed_validators():
    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    total_exited_slashed_index_to_validator = {
        42: Validator(pubkey="0x1234", slashed=False),
        43: Validator(pubkey="0x5678", slashed=False),
    }
    our_exited_slashed_index_to_validator = {
        44: Validator(pubkey="0x9012", slashed=False),
        45: Validator(pubkey="0x3456", slashed=False),
    }

    slashed_validators = SlashedValidators(slack)  # type: ignore

    total_exited_slashed_index_to_validator = {
        42: Validator(pubkey="0x1234", slashed=False),
        43: Validator(pubkey="0x5678", slashed=False),
        44: Validator(pubkey="0x9012", slashed=False),
        45: Validator(pubkey="0x3456", slashed=False),
        46: Validator(pubkey="0xabcd", slashed=False),
    }

    our_exited_slashed_index_to_validator = {
        44: Validator(pubkey="0x9012", slashed=False),
        45: Validator(pubkey="0x3456", slashed=False),
    }

    slashed_validators.process(
        total_exited_slashed_index_to_validator, our_exited_slashed_index_to_validator
    )

    assert total_exited_slashed_validators_count.collect()[0].samples[0].value == 5  # type: ignore
    assert our_exited_slashed_validators_count.collect()[0].samples[0].value == 2  # type: ignore
    assert slack.counter == 0

    assert (
        slashed_validators._SlashedValidators__total_exited_slashed_indexes  # type: ignore
        == {
            42,
            43,
            44,
            45,
            46,
        }
    )

    assert (
        slashed_validators._SlashedValidators__our_exited_slashed_indexes  # type: ignore
        == {44, 45}
    )

    total_exited_slashed_index_to_validator = {
        42: Validator(pubkey="0x1234", slashed=False),
        43: Validator(pubkey="0x5678", slashed=False),
        44: Validator(pubkey="0x9012", slashed=False),
        45: Validator(pubkey="0x3456", slashed=False),
        46: Validator(pubkey="0xabcd", slashed=False),
        47: Validator(pubkey="0xefgh", slashed=False),
    }

    our_exited_slashed_index_to_validator = {
        44: Validator(pubkey="0x9012", slashed=False),
        45: Validator(pubkey="0x3456", slashed=False),
        48: Validator(pubkey="0x5432", slashed=False),
    }

    slashed_validators.process(
        total_exited_slashed_index_to_validator, our_exited_slashed_index_to_validator
    )

    assert total_exited_slashed_validators_count.collect()[0].samples[0].value == 6  # type: ignore
    assert our_exited_slashed_validators_count.collect()[0].samples[0].value == 3  # type: ignore
    assert slack.counter == 1

    assert (
        slashed_validators._SlashedValidators__total_exited_slashed_indexes  # type: ignore
        == {
            42,
            43,
            44,
            45,
            46,
            47,
        }
    )

    assert (
        slashed_validators._SlashedValidators__our_exited_slashed_indexes  # type: ignore
        == {44, 45, 48}
    )
