"""This module contains facilities to keep track of which validator proposes blocks.
"""


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
        """Get the proposer for a slot from the head chain.

        Args:
            slot: int
                The slot to get the proposer for.

        Returns:
            int: The validator index of the proposer, or None if not found.
        """
        return self._head_schedule.get(slot, None)

    def get_finalized_proposer(self, slot: int) -> int:
        """Get the proposer for a slot from the finalized chain.

        Args:
            slot: int
                The slot to get the proposer for.

        Returns:
            int: The validator index of the proposer, or None if not found.
        """
        return self._finalized_schedule.get(slot, None)

    def get_future_proposals(self, slot: int) -> dict[int, int]:
        """Get all future proposals after the given slot.

        Args:
            slot: int
                The current slot to get proposals after.

        Returns:
            dict[int, int]: A dictionary mapping slots to validator indices.
        """
        return {k: v for k, v in self._head_schedule.items() if k > slot}

    def epoch(self, slot: int) -> int:
        """Convert a slot to its epoch.

        Args:
            slot: int
                The slot to convert.

        Returns:
            int: The epoch number containing this slot.
        """
        return slot // self._spec.data.SLOTS_PER_EPOCH

    def update(self, beacon: Beacon, slot: int, last_processed_finalized: int, last_finalized: int) -> None:
        """Update the proposer schedules.

        Updates both the head and finalized proposer schedules.

        Args:
            beacon: Beacon
                The beacon client to fetch data from.
            slot: int
                The current slot.
            last_processed_finalized: int
                The last finalized slot that was processed.
            last_finalized: int
                The current last finalized slot.

        Returns:
            None
        """
        # Current slots & future proposals.

        # There is a case to handle here: on the very first slot of an
        # epoch, some beacons will return 404 and will only expose the
        # schedule on the next slot.

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

    def clear(self, last_processed: int, last_processed_finalized: int) -> None:
        """Clear old slots from the schedules.

        Args:
            last_processed: int
                The last processed slot from the head chain.
            last_processed_finalized: int
                The last processed slot from the finalized chain.

        Returns:
            None
        """
        self._head_schedule = {k: v for k, v in self._head_schedule.items() if k > last_processed}
        self._finalized_schedule = {k: v for k, v in self._finalized_schedule.items() if k > last_processed_finalized}
