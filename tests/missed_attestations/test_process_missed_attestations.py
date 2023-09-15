from typing import Set

from eth_validator_watcher.missed_attestations import process_missed_attestations
from eth_validator_watcher.models import BeaconType, Validators
from eth_validator_watcher.utils import LimitedDict

Validator = Validators.DataItem.Validator


def test_process_missed_attestations_low_epoch() -> None:
    class Beacon:
        pass

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        beacon_type=BeaconType.OLD_TEKU,
        epoch_to_index_to_validator_index=LimitedDict(0),
        epoch=0,
    )

    expected: set[int] = set()

    assert expected == actual


def test_process_missed_attestations_some_dead_indexes() -> None:
    class Beacon:
        @staticmethod
        def get_validators_liveness(
            beacon_type: BeaconType, epoch: int, validators_index: set[int]
        ) -> dict[int, bool]:
            assert beacon_type is BeaconType.OLD_TEKU
            assert epoch == 0
            assert validators_index == {42, 43, 44}

            return {42: False, 43: True, 44: False}

    expected = {42, 44}

    epoch_to_index_to_validator_client = LimitedDict(2)
    epoch_to_index_to_validator_client[0] = {
        42: Validator(pubkey="pubkey42", effective_balance=32000000000, slashed=False),
        43: Validator(pubkey="pubkey43", effective_balance=32000000000, slashed=False),
        44: Validator(pubkey="pubkey44", effective_balance=32000000000, slashed=False),
    }

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        beacon_type=BeaconType.OLD_TEKU,
        epoch_to_index_to_validator_index=epoch_to_index_to_validator_client,
        epoch=1,
    )

    assert expected == actual


def test_process_missed_attestations_no_dead_indexes() -> None:
    class Beacon:
        @staticmethod
        def get_validators_liveness(
            beacon_type: BeaconType, epoch: int, validators_index: set[int]
        ) -> dict[int, bool]:
            assert beacon_type is BeaconType.OLD_TEKU
            assert epoch == 0
            assert validators_index == {42, 43, 44}

            return {}

    expected: Set[int] = set()

    epoch_to_index_to_validator_client = LimitedDict(2)
    epoch_to_index_to_validator_client[0] = {
        42: Validator(pubkey="pubkey42", effective_balance=32000000000, slashed=False),
        43: Validator(pubkey="pubkey43", effective_balance=32000000000, slashed=False),
        44: Validator(pubkey="pubkey44", effective_balance=32000000000, slashed=False),
    }

    actual = process_missed_attestations(
        beacon=Beacon(),  # type: ignore
        beacon_type=BeaconType.OLD_TEKU,
        epoch_to_index_to_validator_index=epoch_to_index_to_validator_client,
        epoch=1,
    )

    assert expected == actual
