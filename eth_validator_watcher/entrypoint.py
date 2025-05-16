"""Main entrypoint module for the Ethereum Validator Watcher."""

from pathlib import Path
from prometheus_client import start_http_server
from pydantic import ValidationError
from typing import Optional

import logging
import typer

from .beacon import Beacon
from .blocks import process_block, process_finalized_block, process_future_blocks
from .coinbase import get_current_eth_price
from .clock import BeaconClock
from .config import load_config
from .duties import process_duties
from .log import log_details, slack_send
from .metrics import get_prometheus_metrics, compute_validator_metrics
from .models import BlockIdentierType, Validators
from .proposer_schedule import ProposerSchedule
from .rewards import process_rewards
from .queues import (
    get_pending_deposits,
    get_pending_consolidations,
    get_pending_withdrawals,
)
from .utils import (
    SLOT_FOR_CONFIG_RELOAD,
    SLOT_FOR_MISSED_ATTESTATIONS_PROCESS,
    SLOT_FOR_REWARDS_PROCESS,
    pct,
)
from .watched_validators import WatchedValidators


app = typer.Typer(add_completion=False)

# This needs to be global for unit tests as there doesn't seem to be a
# way to stop the prometheus HTTP server in a clean way. We have to
# re-use it from test to test and so need to know whether or not it
# was already started.
prometheus_metrics_thread_started = False


class ValidatorWatcher:
    """Main class for the Ethereum Validator Watcher.

    Args:
        None

    Returns:
        None
    """

    def __init__(self, cfg_path: Path) -> None:
        """Initialize the Ethereum Validator Watcher.

        Args:
            cfg_path: Path
                Path to the configuration file.

        Returns:
            None
        """
        self._metrics = get_prometheus_metrics()
        self._metrics_started = False
        self._cfg_path = cfg_path
        self._cfg = None
        self._cfg_last_modified = None
        self._beacon = None
        self._slot_duration = None
        self._genesis = None

        self._reload_config()

        self._spec = self._beacon.get_spec()
        genesis = self._beacon.get_genesis().data.genesis_time

        self._clock = BeaconClock(
            genesis,
            self._spec.data.SECONDS_PER_SLOT,
            self._spec.data.SLOTS_PER_EPOCH,
            self._cfg.replay_start_at_ts,
            self._cfg.replay_end_at_ts,
        )

        self._schedule = ProposerSchedule(self._spec)
        self._slot_hook = None

    def _reload_config(self) -> None:
        """Reload the configuration file and update beacon client if needed.

        Args:
            None

        Returns:
            None
        """
        try:
            if not self._cfg or self._cfg_path.stat().st_mtime != self._cfg_last_modified:
                self._cfg = load_config(str(self._cfg_path))
                self._cfg_last_modified = self._cfg_path.stat().st_mtime
        except ValidationError as err:
            raise typer.BadParameter(f'Invalid configuration file: {err}')

        if self._beacon is None or self._beacon.get_url() != self._cfg.beacon_url or self._beacon.get_timeout_sec() != self._cfg.beacon_timeout_sec:
            self._beacon = Beacon(self._cfg.beacon_url, self._cfg.beacon_timeout_sec)

    def _update_metrics(
            self,
            watched_validators: WatchedValidators,
            epoch: int,
            slot: int,
            pending_deposits: tuple[int, int],
            pending_consolidations: int,
            pending_withdrawals: int,
    ) -> None:
        """Update the Prometheus metrics with the watched validators data.

        Args:
            watched_validators: WatchedValidators
                Registry of validators being watched.
            epoch: int
                Current epoch.
            slot: int
                Current slot.
            pending_deposits: tuple[int, int]
                Number of pending deposits and their total value.
            pending_consolidations: int
                Number of pending consolidations.
            pending_withdrawals: int
                Number of pending withdrawals.

        Returns:
            None
        """
        network = self._cfg.network

        self._metrics.eth_epoch.labels(network).set(epoch)
        self._metrics.eth_slot.labels(network).set(slot)
        self._metrics.eth_current_price_dollars.labels(network).set(get_current_eth_price())

        # Queues

        self._metrics.eth_pending_deposits_count.labels(network).set(pending_deposits[0])
        self._metrics.eth_pending_deposits_value.labels(network).set(pending_deposits[1])
        self._metrics.eth_pending_consolidations_count.labels(network).set(pending_consolidations)
        self._metrics.eth_pending_withdrawals_count.labels(network).set(pending_withdrawals)

        # We iterate once on the validator set to optimize CPU as
        # there is a log of entries here, this makes code here a bit
        # more complex and entangled.

        metrics = compute_validator_metrics(watched_validators.get_validators(), slot)

        log_details(self._cfg, watched_validators, metrics, slot)

        for label, m in metrics.items():
            for status in Validators.DataItem.StatusEnum:
                value = m.validator_status_count.get(status, 0)
                self._metrics.eth_validator_status_count.labels(label, status, network).set(value)
                scaled_value = m.validator_status_scaled_count.get(status, 0.0)
                self._metrics.eth_validator_status_scaled_count.labels(label, status, network).set(scaled_value)

            for consensus_type in [0, 1, 2]:
                value = m.validator_type_count.get(consensus_type, 0)
                self._metrics.eth_validator_type_count.labels(label, consensus_type, network).set(value)
                scaled_value = m.validator_type_scaled_count.get(consensus_type, 0.0)
                self._metrics.eth_validator_type_scaled_count.labels(label, consensus_type, network).set(scaled_value)

        for label, m in metrics.items():
            self._metrics.eth_suboptimal_sources_rate.labels(label, network).set(pct(m.suboptimal_source_count, m.optimal_source_count))
            self._metrics.eth_suboptimal_targets_rate.labels(label, network).set(pct(m.suboptimal_target_count, m.optimal_target_count))
            self._metrics.eth_suboptimal_heads_rate.labels(label, network).set(pct(m.suboptimal_head_count, m.optimal_head_count))

            self._metrics.eth_ideal_consensus_rewards_gwei.labels(label, network).set(m.ideal_consensus_reward)
            self._metrics.eth_actual_consensus_rewards_gwei.labels(label, network).set(m.actual_consensus_reward)
            self._metrics.eth_consensus_rewards_rate.labels(label, network).set(pct(m.actual_consensus_reward, m.ideal_consensus_reward, True))

            self._metrics.eth_missed_attestations_count.labels(label, network).set(m.missed_attestations_count)
            self._metrics.eth_missed_attestations_scaled_count.labels(label, network).set(m.missed_attestations_scaled_count)
            self._metrics.eth_missed_consecutive_attestations_count.labels(label, network).set(m.missed_consecutive_attestations_count)
            self._metrics.eth_missed_consecutive_attestations_scaled_count.labels(label, network).set(m.missed_consecutive_attestations_scaled_count)
            self._metrics.eth_slashed_validators_count.labels(label, network).set(m.validator_slashes)
            self._metrics.eth_missed_duties_at_slot_count.labels(label, network).set(m.missed_duties_at_slot_count)
            self._metrics.eth_missed_duties_at_slot_scaled_count.labels(label, network).set(m.missed_duties_at_slot_scaled_count)
            self._metrics.eth_performed_duties_at_slot_count.labels(label, network).set(m.performed_duties_at_slot_count)
            self._metrics.eth_performed_duties_at_slot_scaled_count.labels(label, network).set(m.performed_duties_at_slot_scaled_count)
            self._metrics.eth_duties_rate.labels(label, network).set(m.duties_rate)
            self._metrics.eth_duties_rate_scaled.labels(label, network).set(m.duties_rate_scaled)

            # Here we inc, it's fine since we previously reset the
            # counters on each run; we can't use set because those
            # metrics are counters.

            self._metrics.eth_block_proposals_head_total.labels(label, network).inc(m.proposed_blocks)
            self._metrics.eth_missed_block_proposals_head_total.labels(label, network).inc(m.missed_blocks)
            self._metrics.eth_block_proposals_finalized_total.labels(label, network).inc(m.proposed_blocks_finalized)
            self._metrics.eth_missed_block_proposals_finalized_total.labels(label, network).inc(m.missed_blocks_finalized)

            self._metrics.eth_future_block_proposals.labels(label, network).set(m.future_blocks_proposal)

        global prometheus_metrics_thread_started
        if not prometheus_metrics_thread_started:
            start_http_server(self._cfg.metrics_port)
            prometheus_metrics_thread_started = True

    def run(self) -> None:
        """Run the Ethereum Validator Watcher main processing loop.

        Args:
            None

        Returns:
            None
        """
        watched_validators = WatchedValidators()
        epoch = self._clock.get_current_epoch()
        slot = self._clock.get_current_slot()

        beacon_validators = None
        validators_liveness = None
        rewards = None
        last_processed_finalized_slot = None
        pending_deposits = None
        pending_consolidations = None
        pending_withdrawals = None

        slack_send(self._cfg, f'🚀 *Ethereum Validator Watcher* started on {self._cfg.network}, watching {len(self._cfg.watched_keys)} validators')

        while True:
            logging.info(f'🔨 Processing slot {slot}')

            last_finalized_slot = self._beacon.get_header(BlockIdentierType.FINALIZED).data.header.message.slot
            self._schedule.update(self._beacon, slot)

            if beacon_validators is None or (slot % self._spec.data.SLOTS_PER_EPOCH == 0):
                logging.info(f'🔨 Processing epoch {epoch}')
                beacon_validators = self._beacon.get_validators(self._clock.epoch_to_slot(epoch))
                watched_validators.process_epoch(beacon_validators)
                if not watched_validators.config_initialized:
                    watched_validators.process_config(self._cfg)

            if pending_deposits is None or (slot % self._spec.data.SLOTS_PER_EPOCH == 0):
                logging.info('🔨 Fetching pending deposits')
                pending_deposits = get_pending_deposits(self._beacon)

            if pending_consolidations is None or (slot % self._spec.data.SLOTS_PER_EPOCH == 0):
                logging.info('🔨 Fetching pending consolidations')
                pending_consolidations = get_pending_consolidations(self._beacon)

            if pending_withdrawals is None or (slot % self._spec.data.SLOTS_PER_EPOCH == 0):
                logging.info('🔨 Fetching pending withdrawals')
                pending_withdrawals = get_pending_withdrawals(self._beacon)

            if validators_liveness is None or (slot % self._spec.data.SLOTS_PER_EPOCH == SLOT_FOR_MISSED_ATTESTATIONS_PROCESS):
                logging.info('🔨 Processing validator liveness')
                validators_liveness = self._beacon.get_validators_liveness(epoch - 1, watched_validators.get_indexes())
                watched_validators.process_liveness(validators_liveness, epoch)

            has_block = self._beacon.has_block_at_slot(slot)

            if rewards is None or (slot % self._spec.data.SLOTS_PER_EPOCH == SLOT_FOR_REWARDS_PROCESS):
                # There is a possibility the slot is missed, in which
                # case we'll have to wait for the next one.
                if not has_block:
                    rewards = None
                else:
                    logging.info('🔨 Trying to process rewards')
                    rewards = self._beacon.get_rewards(epoch - 2)
                    process_rewards(watched_validators, rewards)

            process_block(watched_validators, self._schedule, slot, has_block)
            process_future_blocks(watched_validators, self._schedule, slot)

            while last_processed_finalized_slot and last_processed_finalized_slot < last_finalized_slot:
                logging.info(f'🔨 Processing finalized slot from {last_processed_finalized_slot or last_finalized_slot} to {last_finalized_slot}')
                has_block = self._beacon.has_block_at_slot(last_processed_finalized_slot)
                process_finalized_block(watched_validators, self._schedule, last_processed_finalized_slot, has_block)
                last_processed_finalized_slot += 1
            last_processed_finalized_slot = last_finalized_slot

            logging.info('🔨 Processing committees for previous slot')
            # Here we are looking at attestations in the current slot,
            # which were for the previous slot, this is why we get the
            # previous committees.
            previous_slot_committees = self._beacon.get_committees(slot - 1)
            # But we fetch attestations in the current slot (we expect
            # to find most of what we want for the previous slot).
            # There can be no attestations if the block is entirely
            # missed.
            current_attestations = self._beacon.get_attestations(slot)
            if current_attestations:
                process_duties(watched_validators, previous_slot_committees, current_attestations, slot)

            logging.info('🔨 Updating Prometheus metrics')
            self._update_metrics(watched_validators, epoch, slot, pending_deposits, pending_consolidations, pending_withdrawals)

            if (slot % self._spec.data.SLOTS_PER_EPOCH == SLOT_FOR_CONFIG_RELOAD):
                logging.info('🔨 Processing configuration update')
                self._reload_config()
                watched_validators.process_config(self._cfg)

            self._schedule.clear(last_processed_finalized_slot)
            self._clock.maybe_wait_for_slot(slot + 1)

            if self._slot_hook:
                self._slot_hook(slot)

            if self._cfg.replay_end_at_ts and self._clock.now() >= self._cfg.replay_end_at_ts:
                logging.info('💨 Replay mode ended, exiting')
                break

            slot += 1
            epoch = slot // self._spec.data.SLOTS_PER_EPOCH


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
    """Command line handler to run the Ethereum Validator Watcher.

    Args:
        config: Optional[Path]
            Path to the configuration file.

    Returns:
        None
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s'
    )

    watcher = ValidatorWatcher(config)
    watcher.run()
