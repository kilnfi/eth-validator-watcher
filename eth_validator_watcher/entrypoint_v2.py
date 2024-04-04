"""Draft entrypoint for the eth-validator-watcher v1.0.0.
"""

from functools import partial
from pathlib import Path
from typing import Optional

import logging
import typer
import time

from .beacon import Beacon
from .config import load_config, WatchedKeyConfig
from .utils import (
    SLOT_FOR_MISSED_ATTESTATIONS_PROCESS,
    SLOT_FOR_REWARDS_PROCESS,
)
from .watched_validators import WatchedValidators


app = typer.Typer(add_completion=False)


class BeaconClock:
    """Helper class to keep track of the beacon clock.
    """

    def __init__(self, genesis: int, slot_duration: int, slots_per_epoch: int) -> None:
        self._genesis = genesis
        self._slot_duration = slot_duration
        self._slots_per_epoch = slots_per_epoch

    def get_current_epoch(self, now: float) -> int:
        """Get the current epoch.

        Args:
        -----
        now: float
            Current time in seconds since the epoch.

        Returns:
        --------
        int: Current epoch.
        """
        return self.get_current_slot(now) // self._slots_per_epoch

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

    def get_current_slot(self, now: float) -> int:
        """Get the current slot.

        Args:
        -----
        now: float
            Current time in seconds since the epoch.

        Returns:
        --------
        int: Current slot.
        """
        return int((now - self._genesis) // self._slot_duration)

    def maybe_wait_for_epoch(self, epoch: int, now: float) -> None:
        """Wait for the next epoch.

        Args:
        -----
        epoch: int
            Current epoch.
        now: float
            Current time in seconds since the epoch.
        """
        epoch_start = self.epoch_to_slot(epoch) * self._slot_duration + self._genesis
        time_to_wait = epoch_start - now
        if time_to_wait > 0:
            logging.info(f'Waiting {time_to_wait:.2f} seconds for the next epoch {epoch}')
            time.sleep(time_to_wait)

    def maybe_wait_for_missed_attestations_slot(self, epoch: int, now: float) -> None:
        """Wait for the missed attestations slot.

        Args:
        -----
        epoch: int
            Current epoch.
        now: float
            Current time in seconds since the epoch.
        """
        slot = self.epoch_to_slot(epoch) + SLOT_FOR_MISSED_ATTESTATIONS_PROCESS
        slot_time = slot * self._slot_duration + self._genesis
        time_to_wait = slot_time - now
        if time_to_wait > 0:
            logging.info(f'Waiting {time_to_wait:.2f} seconds for the missed attestations slot {slot}')
            time.sleep(time_to_wait)

    def maybe_wait_for_rewards_slot(self, epoch: int, now: float) -> None:
        """Wait for the rewards slot.

        Args:
        -----
        epoch: int
            Current epoch.
        now: float
            Current time in seconds since the epoch.
        """
        slot = self.epoch_to_slot(epoch) + SLOT_FOR_REWARDS_PROCESS
        slot_time = slot * self._slot_duration + self._genesis
        time_to_wait = slot_time - now
        if time_to_wait > 0:
            logging.info(f'Waiting {time_to_wait:.2f} seconds for the rewards slot {slot}')
            time.sleep(time_to_wait)


class ValidatorWatcher:
    """Ethereum Validator Watcher.
    """

    def __init__(self, cfg_path: Path) -> None:
        """Initialize the Ethereum Validator Watcher.

        Args:
        -----
        cfg_path: Path
            Path to the configuration file.
        """
        self._cfg_path = cfg_path
        self._cfg = None
        self._beacon = None
        self._slot_duration = None
        self._genesis = None

        self._reload_config()

        spec = self._beacon.get_spec()        
        genesis = self._beacon.get_genesis().data.genesis_time

        self._clock = BeaconClock(
            genesis,
            spec.data.SECONDS_PER_SLOT,
            spec.data.SLOTS_PER_EPOCH,
        )

    def _reload_config(self) -> None:
        """Reload the configuration file.
        """
        try:
            self._cfg = load_config(self._cfg_path)
        except ValidationError as err:
            raise typer.BadParameter(f'Invalid configuration file: {err}')

        if self._beacon is None or self._beacon.get_url() != self._cfg.beacon_url or self._beacon.get_timeout_sec() != self._cfg.beacon_timeout_sec:
            self._beacon = Beacon(self._cfg.beacon_url, self._cfg.beacon_timeout_sec)

    def run(self) -> None:
        """Run the Ethereum Validator Watcher.
        """
        watched_validators = WatchedValidators()

        epoch = self._clock.get_current_epoch(time.time())

        while True:
            logging.info(f'Processing epoch {epoch}')
            self._clock.maybe_wait_for_epoch(epoch, time.time())
            beacon_validators = self._beacon.get_validators(self._clock.epoch_to_slot(epoch))
            watched_validators.process_epoch(beacon_validators)

            logging.info('Processing configuration update')
            self._reload_config()
            watched_validators.process_config(self._cfg)

            logging.info('Processing missed attestations')
            self._clock.maybe_wait_for_missed_attestations_slot(epoch, time.time())

            logging.info('Processing rewards')
            self._clock.maybe_wait_for_rewards_slot(epoch, time.time())

            epoch += 1



@app.command()
def handler(
    config: Optional[Path] = typer.Option(
        'etc/config.local.yaml',
        help="File containing the Ethereum Validator Watcher configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        show_default=True,
    ),
) -> None:
    """Run the Ethereum Validator Watcher."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s'
    )

    watcher = ValidatorWatcher(config)
    watcher.run()
