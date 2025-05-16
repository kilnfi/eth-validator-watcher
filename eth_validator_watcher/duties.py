from .models import (
    Attestations,
    Committees,
)
from .watched_validators import WatchedValidators


def bitfield_to_bitstring(ssz: str, strip_length: bool) -> str:
    """Helper to decode an SSZ Bitvector[64].

    This is a bit tricky since we need to have MSB representation
    while Python is LSB oriented. We extract each successive byte from
    the hex representation (2 hex digits per byte), convert to binary
    representation (LSB), pad it, then reverse it to be MSB.
    """
    ssz = ssz.replace('0x', '')

    assert len(ssz) % 2 == 0

    bitstr = ''

    for i in range(int(len(ssz) / 2)):
        bin_repr_lsb = bin(int(ssz[i * 2:(i + 1) * 2], 16)).replace('0b', '')
        bin_repr_lsb_padded = bin_repr_lsb.rjust(8, '0')
        bin_repr_msb = ''.join(reversed(bin_repr_lsb_padded))
        bitstr += bin_repr_msb

    # Bitlists's last bit set to 1 marks the end of the field, we need
    # to strip it to have the final set.
    if strip_length:
        bitstr = bitstr[0:bitstr.rfind('1')]

    return bitstr


def process_duties(watched_validators: WatchedValidators, previous_slot_committees: Committees, current_attestations: Attestations, current_slot: int):
    """Process validator attestation duties for the current slot.

    The current slot contains attestations from the previous slot (and
    potentially older ones).  A validator is considered to have
    performed its duties if in the current slot it attested for the
    previous slot.

    The format is a bit tricky to get right here: attestations are
    aggregated per committees and each committee handles a subset of
    validators, there are 64 committees.

    Each attestation is composed of two bitfields:

    - committee_bits: 64 entries are present, if set to 1 there are
      attestations for validators inside this committee,
    - aggregation_bits: length of this bitfield is the SUM(len) of
      validators in active committees.

    This works well because there is usually way less "attestation
    flavors" on a specific flow, most of the network will vote for the
    same thing under normal condition, so there is usually one entry
    with most committee bits sets and aggregation bits. There may be
    4-5 different flavors, but most of the time this is less than the
    64 committees so this format is efficient.

    This is defined in the consensus specs as follows:

    ```
    def get_attesting_indices(state: BeaconState, attestation: Attestation) -> Set[ValidatorIndex]:
        output: Set[ValidatorIndex] = set()
        committee_indices = get_committee_indices(attestation.committee_bits)
        committee_offset = 0
        for index in committee_indices:
            committee = get_beacon_committee(state, attestation.data.slot, index)
            committee_attesters = set(
                index for i, index in enumerate(committee) if attestation.aggregation_bits[committee_offset + i])
             output = output.union(committee_attesters)
             committee_offset += len(committee)
        return output
    ```

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

    for attestation in current_attestations.data:
        # Here we are interested in attestations against the previous
        # slot, we dismiss whatever is for a prior slot. The goal of
        # this metric is to have a real-time view of optimal
        # performances.
        slot = attestation.data.slot
        if slot != current_slot - 1:
            continue

        committee_indices = bitfield_to_bitstring(attestation.committee_bits, False)
        aggregation_bits = bitfield_to_bitstring(attestation.aggregation_bits, True)

        committee_offset = 0
        for index, exists in enumerate(committee_indices):
            if exists == "1":
                validators_in_committee = committees_lookup[index]
                for i in range(len(validators_in_committee)):
                    if aggregation_bits[committee_offset + i] == "1":
                        validator_index = validators_in_committee[i]
                        validator_duty_performed[validator_index] = True
                committee_offset += len(validators_in_committee)

    # Update validators
    for validator, ok in validator_duty_performed.items():
        v = watched_validators.get_validator_by_index(validator)
        # Here we keep both the current slot and the corresponding value,
        # this is to avoid iterating over the entire validator set: in
        # the compute metrics code we check the slot_id with the
        # currently being processed, if it matches we consider the
        # value up-to-date. If it doesn't, it means it corresponds to
        # its attestation from the previous epoch and the validator
        # didn't perform on this slot.
        v.process_duties(current_slot, ok)
