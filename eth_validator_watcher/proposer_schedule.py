"""This module contains facilities to keep track of which validator proposes blocks.
"""

from dataclasses import dataclass

from .beacon import Beacon
from .models import Spec


class ProposerSchedule:
    """Helper class to keep track of which validator proposes blocks.

    We need to keep track of all slots since the last finalization and
    up to the end of the next epoch.
    """

    def __init__(self, spec: Spec):
        self._spec = spec
        self._last_slot = None
        self._head_schedule = dict()
        self._finalized_schedule = dict()

    def get_head_proposer(self, slot: int) -> int:
        return self._head_schedule.get(slot, None)

    def get_finalized_proposer(self, slot: int) -> int:
        return self._finalized_schedule.get(slot, None)

    def epoch(self, slot: int) -> int:
        return slot // self._spec.data.SLOTS_PER_EPOCH

    def update(self, beacon: Beacon, slot: int, last_processed_finalized: int, last_finalized: int) -> None:
        # Current slots & future proposals.
        epoch = self.epoch(slot)
        if slot not in self._head_schedule:
            duties = beacon.get_proposer_duties(epoch)
            for duty in duties.data:
                self._head_schedule[duty.slot] = duty.validator_index
        if (slot + self._spec.data.SLOTS_PER_EPOCH) not in self._head_schedule:
            duties = beacon.get_proposer_duties(epoch + 1)
            for duty in duties.data:
                self._head_schedule[duty.slot] = duty.validator_index

        # Finalized slots.
        if not last_processed_finalized:
            last_processed_finalized = last_finalized
        for slot in range(last_processed_finalized, last_finalized + 1):
            if slot not in self._finalized_schedule:
                duties = beacon.get_proposer_duties(self.epoch(slot))
                for duty in duties.data:
                    self._finalized_schedule[duty.slot] = duty.validator_index

    def clear(self, last_processed: int, last_processed_finalized) -> None:
        self._head_schedule = {k: v for k, v in self._head_schedule.items() if k > last_processed}
        self._finalized_schedule = {k: v for k, v in self._finalized_schedule.items() if k > last_processed_finalized}
