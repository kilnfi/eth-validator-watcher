import json
from datetime import datetime
from os import environ
from pathlib import Path
from time import sleep
from typing import List, Optional

import requests
import typer
from prometheus_client import Gauge, start_http_server
from sseclient import SSEClient
from typer import Option

from .beacon import Beacon
from .coinbase import Coinbase
from .missed_attestations import (
    process_double_missed_attestations,
    process_missed_attestations,
)
from .missed_blocks import process_missed_blocks
from .models import EventBlock
from .next_blocks_proposal import process_future_blocks_proposal
from .suboptimal_attestations import process_suboptimal_attestations
from .utils import (
    BLOCK_NOT_ORPHANED_TIME,
    NB_SLOT_PER_EPOCH,
    SLOT_FOR_MISSED_ATTESTATIONS_PROCESS,
    Slack,
    get_our_pubkeys,
    write_liveness_file,
)
from .web3signer import Web3Signer

app = typer.Typer()

slot_gauge = Gauge("slot", "Slot")
epoch_gauge = Gauge("epoch", "Epoch")


@app.command()
def handler(
    beacon_url: str = Option(..., help="URL of beacon node"),
    pubkeys_file_path: Optional[Path] = Option(
        None,
        help="File containing the list of public keys to watch",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    web3signer_url: Optional[str] = Option(
        None, help="URL to web3signer managing keys to watch"
    ),
    slack_channel: Optional[str] = Option(
        None, help="Slack channel to send alerts - SLACK_TOKEN env var must be set"
    ),
    liveness_file: Optional[Path] = Option(None, help="Liveness file"),
) -> None:
    """
    🚨 Ethereum Validator Watcher 🚨

    \b
    This tool watches the 🥓 Ethereum Beacon chain 🥓 and tells you when some of your
    validators:
    - missed a block proposal
    - are going to propose a block in the next two epochs
    - did not attest optimally
    - missed an attestation
    - missed two attestations in a raw

    \b
    This tool also exposes extra data as how many validators are active, pending, etc...

    \b
    You can specify:
    - the path to a file containing the list of public your keys to watch, or / and
    - an URL to a Web3Signer instance managing your keys to watch.

    \b
    Pubkeys are load dynamically, at each epoch start.
    - If you use pubkeys file, you can change it without having to restart the watcher.
    - If you use Web3Signer, a call to Web3Signer will be done at every epoch to get the
    latest set of keys to watch.

    Prometheus server is automatically exposed on port 8000.
    """
    _handler(  # pragma: no cover
        beacon_url, pubkeys_file_path, web3signer_url, slack_channel, liveness_file
    )


def _handler(
    beacon_url: str,
    pubkeys_file_path: Optional[Path],
    web3signer_url: Optional[str],
    slack_channel: Optional[str],
    liveness_file: Optional[Path],
) -> None:
    slack_token = environ.get("SLACK_TOKEN")

    if slack_channel is not None and slack_token is None:
        raise typer.BadParameter(
            "SLACK_TOKEN env var must be set if you want to use slack_channel"
        )

    slack = (
        Slack(slack_channel, slack_token)
        if slack_channel is not None and slack_token is not None
        else None
    )

    start_http_server(8000)

    beacon = Beacon(beacon_url)
    coinbase = Coinbase()

    web3signer = Web3Signer(web3signer_url) if web3signer_url is not None else None

    our_pubkeys: set[str] = set()
    our_active_index_to_pubkey: dict[int, str] = {}
    our_dead_indexes: set[int] = set()
    previous_dead_indexes: set[int] = set()

    previous_slot: Optional[int] = None
    previous_epoch: Optional[int] = None

    last_missed_attestations_process_epoch: Optional[int] = None

    event_response = requests.get(
        f"{beacon_url}/eth/v1/events",
        stream=True,
        params=dict(topics="block"),
        headers=dict(Accept="text/event-stream"),
    )

    for event in SSEClient(event_response).events():
        time_slot_start = datetime.now()

        data_dict = json.loads(event.data)
        slot = EventBlock(**data_dict).slot
        epoch = slot // NB_SLOT_PER_EPOCH
        slot_in_epoch = slot % NB_SLOT_PER_EPOCH

        slot_gauge.set(slot)
        epoch_gauge.set(epoch)

        is_new_epoch = previous_epoch is None or previous_epoch != epoch

        if is_new_epoch:
            our_pubkeys = get_our_pubkeys(pubkeys_file_path, web3signer)
            our_active_index_to_pubkey = beacon.get_active_index_to_pubkey(our_pubkeys)
            beacon.get_pending_index_to_pubkey(our_pubkeys)
            coinbase.emit_eth_usd_conversion_rate()

        if previous_epoch is not None and previous_epoch != epoch:
            print(f"🎂     Epoch     {epoch}     starts")

        time_now = datetime.now()
        delta = BLOCK_NOT_ORPHANED_TIME - (time_now - time_slot_start)
        delta_secs = delta.total_seconds()

        should_process_missed_attestations = (
            last_missed_attestations_process_epoch is None
            or (
                last_missed_attestations_process_epoch != epoch
                and slot_in_epoch >= SLOT_FOR_MISSED_ATTESTATIONS_PROCESS
            )
        )

        if should_process_missed_attestations:
            our_dead_indexes = process_missed_attestations(
                beacon, our_active_index_to_pubkey, epoch
            )

            process_double_missed_attestations(
                our_dead_indexes,
                previous_dead_indexes,
                our_active_index_to_pubkey,
                epoch,
                slack,
            )

            last_missed_attestations_process_epoch = epoch

        process_future_blocks_proposal(beacon, our_pubkeys, slot, is_new_epoch)

        sleep(max(0, delta_secs))

        potential_block = beacon.get_potential_block(slot)

        if potential_block is not None:
            process_suboptimal_attestations(
                beacon,
                potential_block,
                slot,
                our_active_index_to_pubkey,
            )

        process_missed_blocks(
            beacon,
            potential_block,
            slot,
            previous_slot,
            our_pubkeys,
            slack,
        )

        previous_dead_indexes = our_dead_indexes
        previous_slot = slot
        previous_epoch = epoch

        if slot_in_epoch >= SLOT_FOR_MISSED_ATTESTATIONS_PROCESS:
            should_process_missed_attestations = True

        if liveness_file is not None:
            write_liveness_file(liveness_file)
