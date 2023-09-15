from typing import Set

from eth_validator_watcher.missed_attestations import process_double_missed_attestations
from eth_validator_watcher.models import Validators
from eth_validator_watcher.utils import LimitedDict

Validator = Validators.DataItem.Validator


def test_process_double_missed_attestations_low_epoch() -> None:
    for epoch in 0, 1:
        actual = process_double_missed_attestations(
            {42, 43, 44, 45},
            {40, 41, 42, 43},
            LimitedDict(0),
            epoch,
            None,
        )

        expected: set[int] = set()

        assert expected == actual


def test_process_double_missed_attestations_some_dead_indexes() -> None:
    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    epoch_to_index_to_validator_index = LimitedDict(2)
    epoch_to_index_to_validator_index[1663] = {
        40: Validator(pubkey="pubkey40", effective_balance=32000000000, slashed=False),
        41: Validator(pubkey="pubkey41", effective_balance=32000000000, slashed=False),
        42: Validator(pubkey="pubkey42", effective_balance=32000000000, slashed=False),
        43: Validator(pubkey="pubkey43", effective_balance=32000000000, slashed=False),
        44: Validator(pubkey="pubkey44", effective_balance=32000000000, slashed=False),
        45: Validator(pubkey="pubkey45", effective_balance=32000000000, slashed=False),
    }

    actual = process_double_missed_attestations(
        {42, 43, 44, 45},
        {40, 41, 42, 43},
        epoch_to_index_to_validator_index,
        1664,
        slack,  # type: ignore
    )

    expected = {42, 43}
    assert expected == actual
    assert slack.counter == 1


def test_process_double_missed_attestations_no_dead_indexes() -> None:
    epoch_to_index_to_validator_index = LimitedDict(2)
    epoch_to_index_to_validator_index[1663] = {
        40: Validator(pubkey="pubkey40", effective_balance=32000000000, slashed=False),
        41: Validator(pubkey="pubkey41", effective_balance=32000000000, slashed=False),
        42: Validator(pubkey="pubkey42", effective_balance=32000000000, slashed=False),
        43: Validator(pubkey="pubkey43", effective_balance=32000000000, slashed=False),
        44: Validator(pubkey="pubkey44", effective_balance=32000000000, slashed=False),
        45: Validator(pubkey="pubkey45", effective_balance=32000000000, slashed=False),
    }

    actual = process_double_missed_attestations(
        {44, 45},
        {40, 41},
        epoch_to_index_to_validator_index,
        1664,
        None,
    )

    excepted: Set[int] = set()
    assert excepted == actual
