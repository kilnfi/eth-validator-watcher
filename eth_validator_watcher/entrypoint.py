"""Draft entrypoint for the eth-validator-watcher v1.0.0.
"""

from collections import defaultdict
from functools import partial
from pathlib import Path
from prometheus_client import start_http_server
from pydantic import ValidationError
from typing import Optional

import logging
import typer
import time

from .coinbase import  get_current_eth_price
from .clock import BeaconClock
from .beacon import Beacon, NoBlockError
from .config import load_config, WatchedKeyConfig
from .metrics import get_prometheus_metrics, compute_validator_metrics, AggregatedMetricsByLabel
from .blocks import process_block, process_finalized_block, process_future_blocks
from .models import BlockIdentierType, Validators
from .rewards import process_rewards
from .utils import (
    SLOT_FOR_CONFIG_RELOAD,
    SLOT_FOR_MISSED_ATTESTATIONS_PROCESS,
    SLOT_FOR_REWARDS_PROCESS,
    pct,
)
from .proposer_schedule import ProposerSchedule
from .watched_validators import WatchedValidators


app = typer.Typer(add_completion=False)


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
            self._cfg.start_at
        )

        self._schedule = ProposerSchedule(self._spec)

    def _reload_config(self) -> None:
        """Reload the configuration file.
        """
        try:
            if not self._cfg or self._cfg_path.stat().st_mtime != self._cfg_last_modified:
                self._cfg = load_config(str(self._cfg_path))
                self._cfg_last_modified = self._cfg_path.stat().st_mtime
        except ValidationError as err:
            raise typer.BadParameter(f'Invalid configuration file: {err}')

        if self._beacon is None or self._beacon.get_url() != self._cfg.beacon_url or self._beacon.get_timeout_sec() != self._cfg.beacon_timeout_sec:
            self._beacon = Beacon(self._cfg.beacon_url, self._cfg.beacon_timeout_sec)

    def _update_metrics(self, watched_validators: WatchedValidators, epoch: int, slot: int) -> None:
        """Update the Prometheus metrics with the watched validators.

        Args:
        -----
        watched_validators: Watched validators.
        epoch: Current epoch.
        slot: Current slot.
        """
        network = self._cfg.network

        self._metrics.eth_epoch.labels(network).set(epoch)
        self._metrics.eth_slot.labels(network).set(slot)
        self._metrics.eth_current_price_dollars.labels(network).set(get_current_eth_price())

        # We iterate once on the validator set to optimize CPU as
        # there is a log of entries here, this makes code here a bit
        # more complex and entangled.

        metrics = compute_validator_metrics(watched_validators.get_validators(), slot)

        for label, m in metrics.items():
            for status in Validators.DataItem.StatusEnum:
                value = m.validator_status_count.get(status, 0)
                self._metrics.eth_validator_status_count.labels(label, status, network).set(value)

        for label, m in metrics.items():
            self._metrics.eth_suboptimal_sources_rate.labels(label, network).set(pct(m.suboptimal_source_count, m.optimal_source_count))
            self._metrics.eth_suboptimal_targets_rate.labels(label, network).set(pct(m.suboptimal_target_count, m.optimal_target_count))
            self._metrics.eth_suboptimal_heads_rate.labels(label, network).set(pct(m.suboptimal_head_count, m.optimal_head_count))

            self._metrics.eth_ideal_consensus_rewards_gwei.labels(label, network).set(m.ideal_consensus_reward)
            self._metrics.eth_actual_consensus_rewards_gwei.labels(label, network).set(m.actual_consensus_reward)
            self._metrics.eth_consensus_rewards_rate.labels(label, network).set(pct(m.actual_consensus_reward, m.ideal_consensus_reward, True))

            self._metrics.eth_missed_attestations_count.labels(label, network).set(m.missed_attestations)
            self._metrics.eth_missed_consecutive_attestations_count.labels(label, network).set(m.missed_consecutive_attestations)
            self._metrics.eth_slashed_validators_count.labels(label, network).set(m.validator_slashes)

            # Here we inc, it's fine since we previously reset the
            # counters on each run; we can't use set because those
            # metrics are counters.

            self._metrics.eth_block_proposals_head_total.labels(label, network).inc(m.proposed_blocks)
            self._metrics.eth_missed_block_proposals_head_total.labels(label, network).inc(m.missed_blocks)
            self._metrics.eth_block_proposals_finalized_total.labels(label, network).inc(m.proposed_finalized_blocks)
            self._metrics.eth_missed_block_proposals_finalized_total.labels(label, network).inc(m.missed_finalized_blocks)

            self._metrics.eth_future_block_proposals.labels(label, network).set(m.future_blocks)

        if not self._metrics_started:
            start_http_server(self._cfg.metrics_port)
            self._metrics_started = True


    def run(self) -> None:
        """Run the Ethereum Validator Watcher.
        """
        watched_validators = WatchedValidators()
        epoch = self._clock.get_current_epoch()
        slot = self._clock.get_current_slot()

        beacon_validators = None
        validators_liveness = None
        rewards = None
        last_processed_finalized_slot = None

        while True:
            logging.info(f'Processing slot {slot}')

            last_finalized_slot = self._beacon.get_header(BlockIdentierType.FINALIZED).data.header.message.slot
            self._schedule.update(self._beacon, slot, last_processed_finalized_slot, last_finalized_slot)

            if beacon_validators == None or (slot % self._spec.data.SLOTS_PER_EPOCH == 0):
                logging.info(f'Processing epoch {epoch}')
                beacon_validators = self._beacon.get_validators(self._clock.epoch_to_slot(epoch))
                watched_validators.process_epoch(beacon_validators)

            if validators_liveness == None or (slot % self._spec.data.SLOTS_PER_EPOCH == SLOT_FOR_MISSED_ATTESTATIONS_PROCESS):
                logging.info('Processing validator liveness')
                validators_liveness = self._beacon.get_validators_liveness(epoch - 1, watched_validators.get_indexes())
                watched_validators.process_liveness(validators_liveness)
 
            if rewards == None or (slot % self._spec.data.SLOTS_PER_EPOCH == SLOT_FOR_REWARDS_PROCESS):
                logging.info('Processing rewards')
                rewards = self._beacon.get_rewards(epoch - 2)
                process_rewards(watched_validators, rewards)

            has_block = self._beacon.has_block_at_slot(slot)

            process_block(watched_validators, self._schedule, slot, has_block)
            process_future_blocks(watched_validators, self._schedule, slot)

            while last_processed_finalized_slot and last_processed_finalized_slot < last_finalized_slot:
                logging.info(f'Processing finalized slot from {last_processed_finalized_slot or last_finalized_slot} to {last_finalized_slot}')
                has_block = self._beacon.has_block_at_slot(last_processed_finalized_slot)
                process_finalized_block(watched_validators, self._schedule, last_processed_finalized_slot, has_block)
                last_processed_finalized_slot += 1
            last_processed_finalized_slot = last_finalized_slot

            logging.info('Updating Prometheus metrics')
            self._update_metrics(watched_validators, epoch, slot)

            if (slot % self._spec.data.SLOTS_PER_EPOCH == SLOT_FOR_CONFIG_RELOAD):
                logging.info('Processing configuration update')
                self._reload_config()
                watched_validators.process_config(self._cfg)

            self._schedule.clear(slot, last_processed_finalized_slot)
            self._clock.maybe_wait_for_slot(slot + 1)

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
    """Run the Ethereum Validator Watcher."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s'
    )

    watcher = ValidatorWatcher(config)
    watcher.run()
