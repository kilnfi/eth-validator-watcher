from .proposer_schedule import ProposerSchedule
from .watched_validators import WatchedValidators


def process_block(validators: WatchedValidators, schedule: ProposerSchedule, slot_id: int, has_block: bool) -> None:
    """Process a block from the head (non-finalized) chain.

    Args:
        validators: WatchedValidators
            The registry of validators being watched.
        schedule: ProposerSchedule
            The proposer schedule to look up who was supposed to propose.
        slot_id: int
            The slot ID being processed.
        has_block: bool
            Whether a block was found in this slot.

    Returns:
        None
    """
    validator_index = schedule.get_proposer(slot_id)
    if validator_index is None:
        return

    validator = validators.get_validator_by_index(validator_index)
    if validator is None:
        return

    validator.process_block(slot_id, has_block)


def process_finalized_block(validators: WatchedValidators, schedule: ProposerSchedule, slot_id: int, has_block: bool) -> None:
    """Process a block from the finalized chain.

    Args:
        validators: WatchedValidators
            The registry of validators being watched.
        schedule: ProposerSchedule
            The proposer schedule to look up who was supposed to propose.
        slot_id: int
            The slot ID being processed.
        has_block: bool
            Whether a block was found in this slot.

    Returns:
        None
    """
    validator_index = schedule.get_proposer(slot_id)
    if validator_index is None:
        return

    validator = validators.get_validator_by_index(validator_index)
    if validator is None:
        return

    validator.process_block_finalized(slot_id, has_block)


def process_future_blocks(validators: WatchedValidators, schedule: ProposerSchedule, slot_id: int) -> None:
    """Process future block proposals based on the proposer schedule.

    Args:
        validators: WatchedValidators
            The registry of validators being watched.
        schedule: ProposerSchedule
            The proposer schedule containing future proposals.
        slot_id: int
            The current slot ID (future proposals will be after this).

    Returns:
        None
    """
    future_proposals = schedule.get_future_proposals(slot_id)

    for slot_id, validator_index in future_proposals.items():
        validator = validators.get_validator_by_index(validator_index)
        if validator is None:
            continue

        validator.process_future_block(slot_id)
