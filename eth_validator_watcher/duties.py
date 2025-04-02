from .models import (
    Attestations,
    Committees,
)
from .watched_validators import WatchedValidators


def hex_to_sparse_bitset(hex_string: str) -> set[int]:
    """Convert a hex string to a set of bits indexes.
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


def process_duties(watched_validators: WatchedValidators, previous_slot_committees: Committees, current_attestations: Attestations, slot_id: int):
    """Process duties.
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
        if slot != slot_id:
            continue
        bitsets = hex_to_sparse_bitset(attestation.aggregation_bits)
        for validator_idx_in_committee in bitsets:
            validator_index = committees_lookup[committee_index][validator_idx_in_committee]
            validator_duty_performed[validator_index] = True

    # Update validators
    for validator in validator_duty_performed:
        v = watched_validators.get_validator_by_index(validator)
        # Here we keep both the last slot and the corresponding value,
        # this is to avoid iterating over the entire validator set: in
        # the compute metrics code we check the slot_id with the
        # currently being processed, if it matches we consider the
        # value up-to-date. If it doesn't, it means it corresponds to
        # its attestation from the previous epoch and the validator
        # didn't perform on this slot.
        v.duties_last_slot = slot_id
        v.duties_last_slot_attested = validator_duty_performed[validator]
