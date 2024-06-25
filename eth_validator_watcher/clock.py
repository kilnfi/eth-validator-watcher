import time
import logging


class BeaconClock:
    """Helper class to keep track of the beacon clock.

    This clock is slightly skewed to ensure we have the data for the
    slot we are processing: it is possible beacons do not have data
    exactly on slot time, so we wait for ~4 seconds into the next
    slot.
    """

    def __init__(self, genesis: int, slot_duration: int, slots_per_epoch: int, start_at: int | None) -> None:
        self._genesis = genesis
        self._slot_duration = slot_duration
        self._slots_per_epoch = slots_per_epoch
        self._lag_seconds = 4.0
        self._init_at = time.time()
        self._start_at = start_at

        if start_at:
            logging.info(f'⏲️ Starting clock at timestamp @ {start_at} ⏲️')

    def now(self) -> float:
        """Get the current time in seconds since the epoch.

        Returns:
        --------
        float: Current time in seconds since the epoch.
        """
        if self._start_at is not None:
            return self._start_at + time.time() - self._init_at
        return time.time()

    def get_current_epoch(self) -> int:
        """Get the current epoch.

        Returns:
        --------
        int: Current epoch.
        """
        return self.get_current_slot() // self._slots_per_epoch

    def epoch_to_slot(self, epoch: int) -> int:
        """Convert an epoch to a slot.

        Args:
        -----
        epoch: int
            Epoch to convert.

        Returns:
        --------
        int: Slot corresponding to the epoch.
        """
        return epoch * self._slots_per_epoch

    def get_current_slot(self) -> int:
        """Get the current slot.

        Returns:
        --------
        int: Current slot.
        """
        return int((self.now() - self._lag_seconds - self._genesis) // self._slot_duration)

    def maybe_wait_for_slot(self, slot: int) -> None:
        """Wait until the given slot is reached.

        Args:
        -----
        slot: int
            Slot to wait for.
        """
        target = self._genesis + slot * self._slot_duration + self._lag_seconds
        now = self.now()
        if now < target:
            logging.info(f'⏳Waiting {target - now:.2f} seconds for slot {slot} ⏳')
            time.sleep(target - now)
