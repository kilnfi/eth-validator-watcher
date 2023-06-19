from eth_validator_watcher.slashed_validators import (
    SlashedValidators,
    our_slashed_validators_count,
    total_slashed_validators_count,
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

    slashed_validators = SlashedValidators(slack)  # type: ignore

    total_exited_slashed_index_to_validator = {
        42: Validator(pubkey="0x1234", slashed=True),
        43: Validator(pubkey="0x5678", slashed=True),
        44: Validator(pubkey="0x9012", slashed=True),
        45: Validator(pubkey="0x3456", slashed=True),
        46: Validator(pubkey="0xabcd", slashed=True),
    }

    total_withdrawal_index_to_validator = {
        47: Validator(pubkey="0xefgh", slashed=True),
        48: Validator(pubkey="0xijkl", slashed=False),
        49: Validator(pubkey="0xaaaa", slashed=False),
        50: Validator(pubkey="0xbbbb", slashed=True),
    }

    our_exited_slashed_index_to_validator = {
        44: Validator(pubkey="0x9012", slashed=True),
        45: Validator(pubkey="0x3456", slashed=True),
    }

    our_withdrawal_index_to_validator = {
        49: Validator(pubkey="0xaaaa", slashed=False),
        50: Validator(pubkey="0xbbbb", slashed=True),
    }

    slashed_validators.process(
        total_exited_slashed_index_to_validator,
        our_exited_slashed_index_to_validator,
        total_withdrawal_index_to_validator,
        our_withdrawal_index_to_validator,
    )

    assert total_slashed_validators_count.collect()[0].samples[0].value == 7  # type: ignore
    assert our_slashed_validators_count.collect()[0].samples[0].value == 3  # type: ignore
    assert slack.counter == 0

    assert (
        slashed_validators._SlashedValidators__total_exited_slashed_indexes  # type: ignore
        == {42, 43, 44, 45, 46}
    )

    assert (
        slashed_validators._SlashedValidators__our_exited_slashed_indexes  # type: ignore
        == {44, 45}
    )

    total_exited_slashed_index_to_validator = {
        42: Validator(pubkey="0x1234", slashed=True),
        43: Validator(pubkey="0x5678", slashed=True),
        44: Validator(pubkey="0x9012", slashed=True),
        45: Validator(pubkey="0x3456", slashed=True),
        46: Validator(pubkey="0xabcd", slashed=True),
        51: Validator(pubkey="0xffff", slashed=True),
    }

    our_exited_slashed_index_to_validator = {
        44: Validator(pubkey="0x9012", slashed=True),
        45: Validator(pubkey="0x3456", slashed=True),
        52: Validator(pubkey="0xeeee", slashed=True),
    }

    slashed_validators.process(
        total_exited_slashed_index_to_validator,
        our_exited_slashed_index_to_validator,
        total_withdrawal_index_to_validator,
        our_withdrawal_index_to_validator,
    )

    assert total_slashed_validators_count.collect()[0].samples[0].value == 8  # type: ignore
    assert our_slashed_validators_count.collect()[0].samples[0].value == 4  # type: ignore
    assert slack.counter == 1

    assert (
        slashed_validators._SlashedValidators__total_exited_slashed_indexes  # type: ignore
        == {42, 43, 44, 45, 46, 51}
    )

    assert (
        slashed_validators._SlashedValidators__our_exited_slashed_indexes  # type: ignore
        == {44, 45, 52}
    )
