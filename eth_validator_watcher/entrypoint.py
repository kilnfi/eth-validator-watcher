"""Entrypoint for the eth-validator-watcher CLI."""

from os import environ
from pathlib import Path
from time import sleep, time
from typing import List, Optional

import typer
from prometheus_client import Gauge, start_http_server
from typer import Option

from .beacon import Beacon
from .coinbase import Coinbase
from .entry_queue import export_duration_sec as export_entry_queue_duration_sec
from .execution import Execution
from .exited_validators import ExitedValidators
from .fee_recipient import process_fee_recipient
from .missed_attestations import (
    process_double_missed_attestations,
    process_missed_attestations,
)
from .missed_blocks import process_missed_blocks
from .models import BeaconType, Validators
from .next_blocks_proposal import process_future_blocks_proposal
from .slashed_validators import SlashedValidators
from .suboptimal_attestations import process_suboptimal_attestations
from .utils import (
    BLOCK_NOT_ORPHANED_TIME_SEC,
    NB_SLOT_PER_EPOCH,
    SLOT_FOR_MISSED_ATTESTATIONS_PROCESS,
    SLOT_FOR_REWARDS_PROCESS,
    LimitedDict,
    Slack,
    get_our_pubkeys,
    slots,
    write_liveness_file,
    eth1_address_0x_prefixed,
)

from .rewards import process_rewards
from .web3signer import Web3Signer

from .relays import Relays

StatusEnum = Validators.DataItem.StatusEnum


app = typer.Typer(add_completion=False)

slot_gauge = Gauge("slot", "Slot")
epoch_gauge = Gauge("epoch", "Epoch")

our_pending_queued_validators_gauge = Gauge(
    "our_pending_queued_validators_count",
    "Our pending queued validators count",
)

total_pending_queued_validators_gauge = Gauge(
    "total_pending_queued_validators_count",
    "Total pending queued validators count",
)

our_active_validators_gauge = Gauge(
    "our_active_validators_count",
    "Our active validators count",
)

total_active_validators_gauge = Gauge(
    "total_active_validators_count",
    "Total active validators count",
)


@app.command()
def handler(
    beacon_url: str = Option(..., help="URL of beacon node", show_default=False),
    execution_url: str = Option(None, help="URL of execution node", show_default=False),
    pubkeys_file_path: Optional[Path] = Option(
        None,
        help="File containing the list of public keys to watch",
        exists=True,
        file_okay=True,
        dir_okay=False,
        show_default=False,
    ),
    web3signer_url: Optional[str] = Option(
        None, help="URL to web3signer managing keys to watch", show_default=False
    ),
    fee_recipient: Optional[str] = Option(
        None,
        help="Fee recipient address - --execution-url must be set",
        show_default=False,
    ),
    slack_channel: Optional[str] = Option(
        None,
        help="Slack channel to send alerts - SLACK_TOKEN env var must be set",
        show_default=False,
    ),
    beacon_type: BeaconType = Option(
        BeaconType.OTHER,
        case_sensitive=False,
        help=(
            "Use this option if connected to a Teku < 23.6.0, Prysm, Lighthouse or "
            "Nimbus beacon node. "
            "See https://github.com/ConsenSys/teku/issues/7204 for Teku < 23.6.0, "
            "https://github.com/prysmaticlabs/prysm/issues/11581 for Prysm, "
            "https://github.com/sigp/lighthouse/issues/4243 for Lighthouse, "
            "https://github.com/status-im/nimbus-eth2/issues/5019 and "
            "https://github.com/status-im/nimbus-eth2/issues/5138 for Nimbus."
        ),
        show_default=False,
    ),
    relay_url: List[str] = Option(
        [], help="URL of allow listed relay", show_default=False
    ),
    liveness_file: Optional[Path] = Option(
        None, help="Liveness file", show_default=False
    ),
) -> None:
    """
    🚨 Ethereum Validator Watcher 🚨

    \b
    Ethereum Validator Watcher monitors the Ethereum beacon chain in real-time and notifies you when any of your validators:
    - are going to propose a block in the next two epochs
    - missed a block proposal
    - did not optimally attest
    - missed an attestation
    - missed two attestations in a row
    - proposed a block with the wrong fee recipient
    - has exited
    - got slashed
    - proposed a block with an unknown relay
    - did not had optimal source, target or head reward

    \b
    It also exports some general metrics such as:
    - your USD assets under management
    - the total staking market cap
    - epoch and slot
    - the number or total slashed validators
    - ETH/USD conversion rate
    - the number of your queued validators
    - the number of your active validators
    - the number of your exited validators
    - the number of the network queued validators
    - the number of the network active validators
    - the entry queue duration estimation

    \b
    Optionally, you can specify the following parameters:
    - the path to a file containing the list of public your keys to watch, or / and
    - a URL to a Web3Signer instance managing your keys to watch.

    \b
    Pubkeys are dynamically loaded, at each epoch start.
    - If you use pubkeys file, you can change it without having to restart the watcher.
    - If you use Web3Signer, a request to Web3Signer is done at every epoch to get the
    latest set of keys to watch.

    \b
    Finally, this program exports the following sets of data from:
    - Prometheus (you can use a Grafana dashboard to monitor your validators)
    - Slack
    - logs

    Prometheus server is automatically exposed on port 8000.
    """
    _handler(  # pragma: no cover
        beacon_url,
        execution_url,
        pubkeys_file_path,
        web3signer_url,
        fee_recipient,
        slack_channel,
        beacon_type,
        relay_url,
        liveness_file,
    )


def _handler(
    beacon_url: str,
    execution_url: Optional[str],
    pubkeys_file_path: Optional[Path],
    web3signer_url: Optional[str],
    fee_recipient: Optional[str],
    slack_channel: Optional[str],
    beacon_type: BeaconType,
    relays_url: List[str],
    liveness_file: Optional[Path],
) -> None:
    """Just a wrapper to be able to test the handler function"""
    slack_token = environ.get("SLACK_TOKEN")

    if fee_recipient is not None and execution_url is None:
        raise typer.BadParameter(
            "`execution-url` must be set if you want to use `fee-recipient`"
        )

    if fee_recipient is not None:
        try:
            fee_recipient = eth1_address_0x_prefixed(fee_recipient)
        except ValueError:
            raise typer.BadParameter("`fee-recipient` should be a valid ETH1 address")

    if slack_channel is not None and slack_token is None:
        raise typer.BadParameter(
            "SLACK_TOKEN env var must be set if you want to use `slack-channel`"
        )

    slack = (
        Slack(slack_channel, slack_token)
        if slack_channel is not None and slack_token is not None
        else None
    )

    start_http_server(8000)

    beacon = Beacon(beacon_url)
    execution = Execution(execution_url) if execution_url is not None else None
    coinbase = Coinbase()
    web3signer = Web3Signer(web3signer_url) if web3signer_url is not None else None
    relays = Relays(relays_url)

    our_pubkeys: set[str] = set()
    our_active_index_to_validator: dict[int, Validators.DataItem.Validator] = {}
    our_validators_indexes_that_missed_attestation: set[int] = set()
    our_validators_indexes_that_missed_previous_attestation: set[int] = set()
    previous_epoch: Optional[int] = None

    exited_validators = ExitedValidators(slack)
    slashed_validators = SlashedValidators(slack)

    last_missed_attestations_process_epoch: Optional[int] = None
    last_rewards_process_epoch: Optional[int] = None
    epoch_to_our_active_index_to_validator = LimitedDict(2)

    genesis = beacon.get_genesis()

    for slot, slot_start_time_sec in slots(genesis.data.genesis_time):
        epoch = slot // NB_SLOT_PER_EPOCH
        slot_in_epoch = slot % NB_SLOT_PER_EPOCH

        slot_gauge.set(slot)
        epoch_gauge.set(epoch)

        is_new_epoch = previous_epoch is None or previous_epoch != epoch

        if is_new_epoch:
            try:
                our_pubkeys = get_our_pubkeys(pubkeys_file_path, web3signer)
            except ValueError:
                raise typer.BadParameter("Some pubkeys are invalid")

            total_status_to_index_to_validator = (
                beacon.get_status_to_index_to_validator()
            )

            our_status_to_index_to_validator = {
                status: {
                    index: validator
                    for index, validator in validator.items()
                    if validator.pubkey in our_pubkeys
                }
                for status, validator in total_status_to_index_to_validator.items()
            }

            our_pending_queued_index_to_validator = (
                our_status_to_index_to_validator.get(StatusEnum.pendingQueued, {})
            )

            our_pending_queued_validators_gauge.set(
                len(our_pending_queued_index_to_validator)
            )

            our_active_index_to_validator = (
                our_status_to_index_to_validator.get(StatusEnum.activeOngoing, {})
                | our_status_to_index_to_validator.get(StatusEnum.activeExiting, {})
                | our_status_to_index_to_validator.get(StatusEnum.activeSlashed, {})
            )

            epoch_to_our_active_index_to_validator[
                epoch
            ] = our_active_index_to_validator

            our_active_validators_gauge.set(len(our_active_index_to_validator))

            our_exited_unslashed_index_to_validator = (
                our_status_to_index_to_validator.get(StatusEnum.exitedUnslashed, {})
            )

            our_exited_slashed_index_to_validator = (
                our_status_to_index_to_validator.get(StatusEnum.exitedSlashed, {})
            )

            our_withdrawable_index_to_validator = our_status_to_index_to_validator.get(
                StatusEnum.withdrawalPossible, {}
            ) | our_status_to_index_to_validator.get(StatusEnum.withdrawalDone, {})

            total_pending_queued_index_to_validator = (
                total_status_to_index_to_validator.get(StatusEnum.pendingQueued, {})
            )

            nb_total_pending_queued_validators = len(
                total_pending_queued_index_to_validator
            )

            total_pending_queued_validators_gauge.set(
                nb_total_pending_queued_validators
            )

            total_active_index_to_validator = (
                total_status_to_index_to_validator.get(StatusEnum.activeOngoing, {})
                | total_status_to_index_to_validator.get(StatusEnum.activeExiting, {})
                | total_status_to_index_to_validator.get(StatusEnum.activeSlashed, {})
            )

            nb_total_active_validators = len(total_active_index_to_validator)
            total_active_validators_gauge.set(nb_total_active_validators)

            total_exited_slashed_index_to_validator = (
                total_status_to_index_to_validator.get(StatusEnum.exitedSlashed, {})
            )

            total_withdrawable_index_to_validator = (
                total_status_to_index_to_validator.get(
                    StatusEnum.withdrawalPossible, {}
                )
                | total_status_to_index_to_validator.get(StatusEnum.withdrawalDone, {})
            )

            exited_validators.process(
                our_exited_unslashed_index_to_validator,
                our_withdrawable_index_to_validator,
            )

            slashed_validators.process(
                total_exited_slashed_index_to_validator,
                our_exited_slashed_index_to_validator,
                total_withdrawable_index_to_validator,
                our_withdrawable_index_to_validator,
            )

            export_entry_queue_duration_sec(
                nb_total_active_validators, nb_total_pending_queued_validators
            )

            coinbase.emit_eth_usd_conversion_rate()

        if previous_epoch is not None and previous_epoch != epoch:
            print(f"🎂     Epoch     {epoch}     starts")

        should_process_missed_attestations = (
            slot_in_epoch >= SLOT_FOR_MISSED_ATTESTATIONS_PROCESS
            and (
                last_missed_attestations_process_epoch is None
                or last_missed_attestations_process_epoch != epoch
            )
        )

        if should_process_missed_attestations:
            our_validators_indexes_that_missed_attestation = (
                process_missed_attestations(
                    beacon, beacon_type, epoch_to_our_active_index_to_validator, epoch
                )
            )

            process_double_missed_attestations(
                our_validators_indexes_that_missed_attestation,
                our_validators_indexes_that_missed_previous_attestation,
                epoch_to_our_active_index_to_validator,
                epoch,
                slack,
            )

            last_missed_attestations_process_epoch = epoch

        should_process_rewards = slot_in_epoch >= SLOT_FOR_REWARDS_PROCESS and (
            last_rewards_process_epoch is None or last_rewards_process_epoch != epoch
        )

        if should_process_rewards:
            process_rewards(beacon, beacon_type, epoch, our_active_index_to_validator)
            last_rewards_process_epoch = epoch

        process_future_blocks_proposal(beacon, our_pubkeys, slot, is_new_epoch)

        delta_sec = BLOCK_NOT_ORPHANED_TIME_SEC - (time() - slot_start_time_sec)
        sleep(max(0, delta_sec))

        potential_block = beacon.get_potential_block(slot)

        if potential_block is not None:
            block = potential_block

            process_suboptimal_attestations(
                beacon,
                block,
                slot,
                our_active_index_to_validator,
            )

            process_fee_recipient(
                block, our_active_index_to_validator, execution, fee_recipient, slack
            )

        is_our_validator = process_missed_blocks(
            beacon,
            potential_block,
            slot,
            our_pubkeys,
            slack,
        )

        if is_our_validator and potential_block is not None:
            relays.process(slot)

        our_validators_indexes_that_missed_previous_attestation = (
            our_validators_indexes_that_missed_attestation
        )

        previous_epoch = epoch

        if slot_in_epoch >= SLOT_FOR_MISSED_ATTESTATIONS_PROCESS:
            should_process_missed_attestations = True

        if liveness_file is not None:
            write_liveness_file(liveness_file)
