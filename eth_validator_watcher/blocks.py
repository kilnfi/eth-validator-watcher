import logging
import functools

from .proposer_schedule import ProposerSchedule
from .watched_validators import WatchedValidators


def process_block(validators: WatchedValidators, schedule: ProposerSchedule, slot_id: int, has_block: bool):
    validator_index = schedule.get_head_proposer(slot_id)
    if validator_index is None:
        return

    validator = validators.get_validator_by_index(validator_index)
    if validator is None:
        return

    validator.process_block(slot_id, has_block)


def process_finalized_block(validators: WatchedValidators, schedule: ProposerSchedule, slot_id: int, has_block: bool):
    validator_index = schedule.get_finalized_proposer(slot_id)
    if validator_index is None:
        return

    validator = validators.get_validator_by_index(validator_index)
    if validator is None:
        return

    validator.process_block_finalized(slot_id, has_block)


def process_future_blocks(validators: WatchedValidators, schedule: ProposerSchedule, slot_id: int):
    future_proposals = schedule.get_future_proposals(slot_id)

    for slot_id, validator_index in future_proposals.items():
        validator = validators.get_validator_by_index(validator_index)
        if validator is None:
            continue

        validator.process_future_block(slot_id)
