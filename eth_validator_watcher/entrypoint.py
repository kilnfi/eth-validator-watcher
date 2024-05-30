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
from .metrics import get_prometheus_metrics
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
        )

        self._schedule = ProposerSchedule(self._spec)

    def _reload_config(self) -> None:
        """Reload the configuration file.
        """
        try:
            self._cfg = load_config(self._cfg_path)
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

        # Count of validators by status
        validator_status_count: dict[str, dict[str, int]] = defaultdict(partial(defaultdict, int))

        # Gauges
        suboptimal_source_count: dict[str, int] = defaultdict(int)
        suboptimal_target_count: dict[str, int] = defaultdict(int)
        suboptimal_head_count: dict[str, int] = defaultdict(int)
        optimal_source_count: dict[str, int] = defaultdict(int)
        optimal_target_count: dict[str, int] = defaultdict(int)
        optimal_head_count: dict[str, int] = defaultdict(int)
        validator_slashes: dict[str, int] = defaultdict(int)

        # Gauges
        ideal_consensus_reward: dict[str, int] = defaultdict(int)
        actual_consensus_reward: dict[str, int] = defaultdict(int)
        missed_attestations: dict[str, int] = defaultdict(int)
        missed_consecutive_attestations: dict[str, int] = defaultdict(int)

        # Counters
        proposed_blocks: dict[str, int] = defaultdict(int)
        missed_blocks: dict[str, int] = defaultdict(int)
        proposed_finalized_blocks: dict[str, int] = defaultdict(int)
        missed_finalized_blocks: dict[str, int] = defaultdict(int)

        # Gauge
        future_blocks: dict[str, int] = defaultdict(int)

        # All labels and statuses so that we can set to 0 metrics that
        # do not have any value for a given label/status.
        labels = set()
        statuses = set()

        for validator in watched_validators.get_validators().values():

            status = str(validator.status)
            statuses.add(status)
            
            for label in validator.labels:

                labels.add(label)

                validator_status_count[label][status] += 1

                validator_slashes[label] += int(validator.beacon_validator.validator.slashed == True)

                # Everything below implies to have a validator that is
                # active on the beacon chain, this prevents
                # miscounting missed attestation for instance.

                if not validator.is_validating():
                    continue

                # Looks weird but we want to explicitly have labels set
                # for each set of labels even if they aren't validating
                # (in which case the validator attributes are None).

                suboptimal_source_count[label] += int(validator.suboptimal_source == True)
                suboptimal_target_count[label] += int(validator.suboptimal_target == True)
                suboptimal_head_count[label] += int(validator.suboptimal_head == True)
                optimal_source_count[label] += int(validator.suboptimal_source == False)
                optimal_target_count[label] += int(validator.suboptimal_target == False)
                optimal_head_count[label] += int(validator.suboptimal_head == False)

                ideal_consensus_reward[label] += validator.ideal_consensus_reward or 0
                actual_consensus_reward[label] += validator.actual_consensus_reward or 0

                missed_attestations[label] += int(validator.missed_attestation == True)
                missed_consecutive_attestations[label] += int(validator.previous_missed_attestation == True and validator.missed_attestation == True)

                proposed_blocks[label] += validator.proposed_blocks_total
                missed_blocks[label] += validator.missed_blocks_total
                proposed_finalized_blocks[label] += validator.proposed_blocks_finalized_total
                missed_finalized_blocks[label] += validator.missed_blocks_finalized_total

                future_blocks[label] += validator.future_blocks_proposal

            # Here we reset the counters for the next run, we do not
            # touch gauges though.  This ensures we handle properly
            # changes of the labelling in real-time.

            validator.proposed_blocks_total = 0
            validator.missed_blocks_total = 0
            validator.proposed_blocks_finalized_total = 0
            validator.missed_blocks_finalized_total = 0
            validator.future_blocks_proposal = 0


        for label in labels:
            for status in statuses:
                value = validator_status_count.get(label, {}).get(status, 0)
                self._metrics.eth_validator_status_count.labels(label, status, network).set(value)

        for label in labels:
            self._metrics.eth_suboptimal_sources_rate.labels(label, network).set(pct(suboptimal_source_count[label], optimal_source_count[label]))
            self._metrics.eth_suboptimal_targets_rate.labels(label, network).set(pct(suboptimal_target_count[label], optimal_target_count[label]))
            self._metrics.eth_suboptimal_heads_rate.labels(label, network).set(pct(suboptimal_head_count[label], optimal_head_count[label]))

            self._metrics.eth_ideal_consensus_rewards_gwei.labels(label, network).set(ideal_consensus_reward[label])
            self._metrics.eth_actual_consensus_rewards_gwei.labels(label, network).set(actual_consensus_reward[label])
            self._metrics.eth_consensus_rewards_rate.labels(label, network).set(pct(actual_consensus_reward[label], ideal_consensus_reward[label], True))

            self._metrics.eth_missed_attestations_count.labels(label, network).set(missed_attestations[label])
            self._metrics.eth_missed_consecutive_attestations_count.labels(label, network).set(missed_consecutive_attestations[label])
            self._metrics.eth_slashed_validators_count.labels(label, network).set(validator_slashes[label])

            # Here we inc, it's fine since we previously reset the
            # counters on each run; we can't use set because those
            # metrics are counters.

            self._metrics.eth_block_proposals_head_total.labels(label, network).inc(proposed_blocks[label])
            self._metrics.eth_missed_block_proposals_head_total.labels(label, network).inc(missed_blocks[label])
            self._metrics.eth_block_proposals_finalized_total.labels(label, network).inc(proposed_finalized_blocks[label])
            self._metrics.eth_missed_block_proposals_finalized_total.labels(label, network).inc(missed_finalized_blocks[label])

            self._metrics.eth_future_block_proposals.labels(label, network).set(future_blocks[label])

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

            if validators_liveness == None or (slot % SLOT_FOR_MISSED_ATTESTATIONS_PROCESS == 0):
                logging.info('Processing validator liveness')
                validators_liveness = self._beacon.get_validators_liveness(epoch - 1, watched_validators.get_indexes())
                watched_validators.process_liveness(validators_liveness)

            if rewards == None or (slot % SLOT_FOR_REWARDS_PROCESS == 0):
                logging.info('Processing rewards')
                rewards = self._beacon.get_rewards(epoch - 2)
                process_rewards(watched_validators, rewards)

            has_block = self._beacon.has_block_at_slot(slot)

            process_block(watched_validators, self._schedule, slot, has_block)
            process_future_blocks(watched_validators, self._schedule, slot)

            last_finalized_slot = self._beacon.get_header(BlockIdentierType.FINALIZED).data.header.message.slot
            while last_processed_finalized_slot and last_processed_finalized_slot < last_finalized_slot:
                logging.info(f'Processing finalized slot from {last_processed_finalized_slot or last_finalized_slot} to {last_finalized_slot}')
                has_block = self._beacon.has_block_at_slot(last_processed_finalized_slot)
                process_finalized_block(watched_validators, self._schedule, last_processed_finalized_slot, has_block)
                last_processed_finalized_slot += 1
            last_processed_finalized_slot = last_finalized_slot

            if (slot % SLOT_FOR_CONFIG_RELOAD == 0):
                logging.info('Processing configuration update')
                self._reload_config()
                watched_validators.process_config(self._cfg)

            logging.info('Updating Prometheus metrics')
            self._update_metrics(watched_validators, epoch, slot)

            self._schedule.clear(slot, last_processed_finalized_slot)
            self._clock.maybe_wait_for_slot(slot + 1, time.time())

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
