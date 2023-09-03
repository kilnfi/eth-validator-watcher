"""Contains functions to process sub-optimal attestations"""

import functools
from collections import defaultdict

from prometheus_client import Gauge

from .beacon import Beacon
from .models import Block, Validators
from .utils import (
    NB_SLOT_PER_EPOCH,
    aggregate_bools,
    apply_mask,
    convert_hex_to_bools,
    remove_all_items_from_last_true,
    switch_endianness,
)

print = functools.partial(print, flush=True)

suboptimal_attestations_rate_gauge = Gauge(
    "suboptimal_attestations_rate",
    "Suboptimal attestations rate",
)

key_suboptimal_attestations_rate_gauge = Gauge(
    "key_suboptimal_attestations_rate",
    "Key suboptimal attestations",
    ["pubkey"],
)

initialized_keys: set[str] = set()

def process_suboptimal_attestations(
    beacon: Beacon,
    block: Block,
    slot: int,
    our_active_validators_index_to_validator: dict[int, Validators.DataItem.Validator],
) -> set[int]:
    """Process sub-optimal attestations

    Parameters:
    beacon                               : Beacon instance
    block                                : Block to check sub-optimal attestations
                                           against
    slot                                 : Slot of the block
    our_active_validators_index_to_pubkey: dictionnary with:
      - key  : index of our active validator
      - value: public key of our active validator
    """
    for _idx in our_active_validators_index_to_validator:
        if our_active_validators_index_to_validator[_idx].pubkey not in initialized_keys:
            key_suboptimal_attestations_rate_gauge.labels(
                pubkey=our_active_validators_index_to_validator[_idx].pubkey
            )
            initialized_keys.add(our_active_validators_index_to_validator[_idx].pubkey)
    for _key in initialized_keys:
        found = False
        for _idx in our_active_validators_index_to_validator:
            if our_active_validators_index_to_validator[_idx].pubkey == _key:
                found = True
                break
        if not found:
            key_suboptimal_attestations_rate_gauge.remove(_key)
            initialized_keys.remove(_key)

    previous_slot = slot - 1

    # Epoch of previous slot is NOT the previous epoch, but really the epoch
    # corresponding to the previous slot.
    epoch_of_previous_slot = previous_slot // NB_SLOT_PER_EPOCH

    # All our active validators index
    our_active_validators_index = set(our_active_validators_index_to_validator)

    # Nested dictionary
    # - Key of the outer dict is the slot
    # - Value of the outer dict (which is key of the inner dict) is the committee index
    # - Value of the inner dict is the list of validators index that have to attest
    #   during the given slot and for the given committee index
    duty_slot_to_committee_index_to_validators_index: dict[
        int, dict[int, list[int]]
    ] = beacon.get_duty_slot_to_committee_index_to_validators_index(
        epoch_of_previous_slot
    )

    # Dictionary where key is committee index and value is the list of validators
    # index that had to attest during the previous slot
    duty_committee_index_to_validators_index_during_previous_slot = (
        duty_slot_to_committee_index_to_validators_index[previous_slot]
    )

    # Index of validators that had to attest during the previous slot
    validators_index_that_had_to_attest_during_previous_slot = set(
        (
            item
            for sublist in duty_committee_index_to_validators_index_during_previous_slot.values()
            for item in sublist
        )
    )

    # Index ouf our validators that had to attest during the previous slot
    our_validators_index_that_had_to_attest_during_previous_slot = (
        validators_index_that_had_to_attest_during_previous_slot
        & our_active_validators_index
    )

    # Dictionary
    # - Key is the committee index
    # - Value is a list of boolean where each boolean indicates if the validator
    #   attested optimally
    committee_index_to_validator_attestation_success = aggregate_attestations(
        block, previous_slot
    )

    list_of_validators_index_that_attested_optimally_during_previous_slot = (
        apply_mask(
            duty_committee_index_to_validators_index_during_previous_slot[
                actual_committee_index
            ],
            validator_attestation_success,
        )
        for (
            actual_committee_index,
            validator_attestation_success,
        ) in committee_index_to_validator_attestation_success.items()
    )

    # Index of validators which actually attested for the previous slot
    validators_index_that_attested_optimally_during_previous_slot: set[int] = set(
        item
        for sublist in list_of_validators_index_that_attested_optimally_during_previous_slot
        for item in sublist
    )

    # Index of our validators that attested optimally during the previous slot
    our_validators_index_that_attested_optimally_during_previous_slot = (
        validators_index_that_attested_optimally_during_previous_slot
        & our_validators_index_that_had_to_attest_during_previous_slot
    )

    # Index of our validators which failed to attest optimally during the previous slot
    our_validators_index_that_did_not_attest_optimally_during_previous_slot = (
        our_validators_index_that_had_to_attest_during_previous_slot
        - our_validators_index_that_attested_optimally_during_previous_slot
    )

    suboptimal_attestations_rate = (
        len(our_validators_index_that_did_not_attest_optimally_during_previous_slot)
        / len(our_validators_index_that_had_to_attest_during_previous_slot)
        if len(our_validators_index_that_had_to_attest_during_previous_slot) != 0
        else None
    )

    if suboptimal_attestations_rate is not None:
        suboptimal_attestations_rate_gauge.set(100 * suboptimal_attestations_rate)

    if len(our_validators_index_that_did_not_attest_optimally_during_previous_slot) > 0:
        assert suboptimal_attestations_rate is not None

        first_indexes = sorted(
            list(
                our_validators_index_that_did_not_attest_optimally_during_previous_slot
            )
        )[:5]

        first_pubkeys = (
            our_active_validators_index_to_validator[first_index].pubkey
            for first_index in first_indexes
        )

        short_first_pubkeys = [pubkey[:10] for pubkey in first_pubkeys]
        short_first_pubkeys_str = ", ".join(short_first_pubkeys)

        print(
            f"☣️ Our validator {short_first_pubkeys_str} and "
            f"{len(our_validators_index_that_did_not_attest_optimally_during_previous_slot) - len(short_first_pubkeys)} more "
            f"({round(100 * suboptimal_attestations_rate, 1)} %) had not optimal attestation "
            f"inclusion at slot {previous_slot}"
        )

        for _idx in our_validators_index_that_did_not_attest_optimally_during_previous_slot:
            key_suboptimal_attestations_rate_gauge.labels(
                pubkey=our_active_validators_index_to_validator[_idx].pubkey
            ).set(1)
        for _idx in our_validators_index_that_attested_optimally_during_previous_slot:
            key_suboptimal_attestations_rate_gauge.labels(
                pubkey=our_active_validators_index_to_validator[_idx].pubkey
            ).set(0)

    return our_validators_index_that_did_not_attest_optimally_during_previous_slot


def aggregate_attestations(block: Block, slot: int) -> dict[int, list[bool]]:
    """Aggregates all attestations for the slot `slot` that are presient
    in block `block`.

    Parameters:
    block: Block
    slot: Slot

    Returns:
    Each boolean of the list corresponds to a validator in the given committee.
    If the validator attestation from the previous slot is included in the current
    slot, the boolean is True. Else, it is False.
    """
    filtered_attestations = (
        attestation
        for attestation in block.data.message.body.attestations
        if attestation.data.slot == slot
    )

    # TODO: Write this code with dict comprehension
    committee_index_to_list_of_aggregation_bools: dict[
        int, list[list[bool]]
    ] = defaultdict(list)

    for attestation in filtered_attestations:
        aggregated_bits_little_endian_with_last_bit = attestation.aggregation_bits

        # Aggregations bits are given under binary (hexadecimal) shape.
        # We convert bytes to booleans.
        aggregated_bools_little_endian_with_last_bit = convert_hex_to_bools(
            aggregated_bits_little_endian_with_last_bit
        )

        # Aggregations bits are represented in little endian shape.
        # However, validators in committees are listed in big endian shape.
        # We switch endianness
        aggregated_bools_with_last_bit = switch_endianness(
            aggregated_bools_little_endian_with_last_bit
        )

        # Aggregations bits in a given committee are represented with one bit for
        # one validator. The number of validators bit is always a multiple of 8,
        # even if the number of validators is not a multiple of 8.
        # The last `1` (or last `True` in our boolean list) represents the boundary.
        # All following `0`s can be ignored, as they do not represent validators
        # As a consequence, we remove the last `1` and all following `0`s
        aggregated_bools = remove_all_items_from_last_true(
            aggregated_bools_with_last_bit
        )

        committee_index_to_list_of_aggregation_bools[attestation.data.index].append(
            aggregated_bools
        )

    # Finally, we aggregate all attestations
    items = committee_index_to_list_of_aggregation_bools.items()

    return {
        committee_index: aggregate_bools(list_of_aggregation_bools)
        for committee_index, list_of_aggregation_bools in items
    }
