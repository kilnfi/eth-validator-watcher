from typing import Set

from eth_validator_watcher.missed_attestations import process_missed_attestations


def test_process_missed_attestations_some_dead_indexes() -> None:
    class Beacon:
        @staticmethod
        def get_validators_liveness(
            lighthouse: bool, epoch: int, validators_index: set[int]
        ) -> dict[int, bool]:
            assert lighthouse is False
            assert epoch == 0
            assert validators_index == {42, 43, 44}

            return {42: False, 43: True, 44: False}

    expected = {42, 44}

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        lighthouse=False,
        our_active_index_to_pubkey={42: "pubkey42", 43: "pubkey43", 44: "pubkey44"},
        epoch=1,
    )

    assert expected == actual


def test_process_missed_attestations_no_dead_indexes() -> None:
    class Beacon:
        @staticmethod
        def get_validators_liveness(
            lighthouse: bool, epoch: int, validators_index: set[int]
        ) -> dict[int, bool]:
            assert lighthouse is False
            assert epoch == 0
            assert validators_index == {42, 43, 44}

            return {}

    expected: Set[int] = set()

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        lighthouse=False,
        our_active_index_to_pubkey={42: "pubkey42", 43: "pubkey43", 44: "pubkey44"},
        epoch=1,
    )

    assert expected == actual
