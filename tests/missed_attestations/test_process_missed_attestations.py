from typing import Set

from eth_validator_watcher.missed_attestations import process_missed_attestations
from eth_validator_watcher.models import BeaconType, Validators

Validator = Validators.DataItem.Validator


def test_process_missed_attestations_some_dead_indexes() -> None:
    class Beacon:
        @staticmethod
        def get_validators_liveness(
            beacon_type: BeaconType, epoch: int, validators_index: set[int]
        ) -> dict[int, bool]:
            assert beacon_type is BeaconType.TEKU
            assert epoch == 0
            assert validators_index == {42, 43, 44}

            return {42: False, 43: True, 44: False}

    expected = {42, 44}

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        beacon_type=BeaconType.TEKU,
        our_active_index_to_validator={
            42: Validator(pubkey="pubkey42", slashed=False),
            43: Validator(pubkey="pubkey43", slashed=False),
            44: Validator(pubkey="pubkey44", slashed=False),
        },
        epoch=1,
    )

    assert expected == actual


def test_process_missed_attestations_no_dead_indexes() -> None:
    class Beacon:
        @staticmethod
        def get_validators_liveness(
            beacon_type: BeaconType, epoch: int, validators_index: set[int]
        ) -> dict[int, bool]:
            assert beacon_type is BeaconType.TEKU
            assert epoch == 0
            assert validators_index == {42, 43, 44}

            return {}

    expected: Set[int] = set()

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        beacon_type=BeaconType.TEKU,
        our_active_index_to_validator={
            42: Validator(pubkey="pubkey42", slashed=False),
            43: Validator(pubkey="pubkey43", slashed=False),
            44: Validator(pubkey="pubkey44", slashed=False),
        },
        epoch=1,
    )

    assert expected == actual
