from typing import Set
from eth_validator_watcher.missed_attestations import (
    process_double_missed_attestations,
)


def test_process_double_missed_attestations_some_dead_indexes() -> None:
    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    actual = process_double_missed_attestations(
        {42, 43, 44, 45},
        {40, 41, 42, 43},
        {
            40: "pubkey40",
            41: "pubkey41",
            42: "pubkey42",
            43: "pubkey43",
            44: "pubkey44",
            45: "pubkey45",
        },
        1664,
        slack,  # type: ignore
    )

    expected = {42, 43}
    assert expected == actual
    assert slack.counter == 1


def test_process_double_missed_attestations_no_dead_indexes() -> None:
    actual = process_double_missed_attestations(
        {44, 45},
        {40, 41},
        {
            40: "pubkey40",
            41: "pubkey41",
            42: "pubkey42",
            43: "pubkey43",
            44: "pubkey44",
            45: "pubkey45",
        },
        1664,
        None,
    )

    excepted: Set[int] = set()
    assert excepted == actual
