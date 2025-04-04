from .models import (
    Attestations,
    Committees,
)
from .watched_validators import WatchedValidators


def hex_to_sparse_bitset(hex_string: str) -> set[int]:
    """Convert a hexadecimal string to a set of bit indices that are set to 1.

    Args:
        hex_string: str
            Hexadecimal string to convert (with or without '0x' prefix).

    Returns:
        set[int]
            Set containing the indices of bits that are set to 1 in the hexadecimal value.
    """
    clean_hex = hex_string.strip().replace('0x', '')
    num = int(clean_hex, 16)
    set_bits = set()
    total_bits = len(clean_hex) * 4

    for i in range(total_bits):
        bit_pos = total_bits - 1 - i
        if num & (1 << i):
            set_bits.add(bit_pos)

    return set_bits


def process_duties(watched_validators: WatchedValidators, previous_slot_committees: Committees, current_attestations: Attestations, current_slot: int):
    """Process validator attestation duties for the current slot.

    The current slot contains attestations from the previous slot (and potentially older ones).
    A validator is considered to have performed its duties if in the current slot it attested
    for the previous slot.

    Args:
        watched_validators: WatchedValidators
            Registry of validators being watched.
        previous_slot_committees: Committees
            Committee assignments for the previous slot.
        current_attestations: Attestations
            Attestations included in the current slot's block.
        current_slot: int
            The current slot being processed.

    Returns:
        None
    """
    validator_duty_performed: dict[int, bool] = {}

    # Prepare the lookup for the committees
    committees_lookup: dict[int, list[int]] = {}
    for committee in previous_slot_committees.data:
        committees_lookup[committee.index] = committee.validators
        for v in committee.validators:
            validator_duty_performed[v] = False

    # Check if the validator has attested
    for attestation in current_attestations.data:
        committee_index = attestation.data.index
        slot = attestation.data.slot
        # Here we are interested in attestations against the previous
        # slot.
        if slot != current_slot - 1:
            continue
        bitsets = hex_to_sparse_bitset(attestation.aggregation_bits)
        for validator_idx_in_committee in bitsets:
            if validator_idx_in_committee >= len(committees_lookup[committee_index]):
                continue
            validator_index = committees_lookup[committee_index][validator_idx_in_committee]
            validator_duty_performed[validator_index] = True

    # Update validators
    for validator in validator_duty_performed:
        v = watched_validators.get_validator_by_index(validator)
        # Here we keep both the current slot and the corresponding value,
        # this is to avoid iterating over the entire validator set: in
        # the compute metrics code we check the slot_id with the
        # currently being processed, if it matches we consider the
        # value up-to-date. If it doesn't, it means it corresponds to
        # its attestation from the previous epoch and the validator
        # didn't perform on this slot.
        v.process_duties(current_slot, validator_duty_performed[validator])
