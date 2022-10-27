import json
import time
from pathlib import Path
from typing import List, Optional

import requests
import sseclient
import typer
from prometheus_client import Counter, Gauge, start_http_server
from typer import Option

from .beacon import Beacon
from .missed_attestations import handle_missed_attestation_detection
from .missed_blocks import handle_missed_block_detection
from .models import DataBlock
from .next_blocks_proposal import handle_next_blocks_proposal
from .utils import get_our_pubkeys, write_liveliness_file
from .web3signer import Web3Signer

app = typer.Typer()


@app.command()
def handler(
    beacon_url: str = Option(..., help="URL of Teku beacon node"),
    pubkeys_file_path: Optional[Path] = Option(
        None,
        help="File containing the list of public keys to watch",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    web3signer_url: Optional[List[str]] = Option(
        None, help="URL to web3signer managing keys to watch"
    ),
    liveliness_file: Optional[Path] = Option(None, help="Liveness file"),
    prometheus_probe_missed_block_proposals: str = Option(
        "eth_validator_watcher_missed_block_proposals",
        help="Prometheus probe name for missed block proposals",
    ),
    prometheus_probe_rate_of_not_optimal_attestation_inclusion: str = Option(
        "eth_validator_watcher_rate_of_not_optimal_attestation_inclusion",
        help="Prometheus probe name for rate of non optimal attestation inclusion",
    ),
    prometheus_probe_number_of_two_not_optimal_attestation_inclusion_in_a_raw: str = Option(
        "eth_validator_watcher_two_not_optimal_attestation_inclusion_in_a_raw",
        help=(
            "Prometheus probe name for number of two non optimal attestation "
            " inclusion in a raw"
        ),
    ),
) -> None:
    """
    🚨 Be alerted when you miss a block proposal / when your attestations are late! 🚨

    \b
    This tool watches the 🥓 Ethereum Beacon chain 🥓 and tells you:
    - when you miss a block proposal
    - when some of your attestations are not optimally included in the next slot
    - when some of your attestations are not optimally included in the next slot two
      times in a raw (may indicates there is an issue with this specific key)
    - if one of your keys are about to propose a block in the next two epochs (useful
      when you want to reboot one of your validator client without pressure)

    \b
    You can specify:
    - the path to a file containing the list of public your keys to watch, or / and
    - an URL to a Web3Signer instance managing your keys to watch.

    \b
    Pubkeys are load dynamically, on the first slot of each epoch.
    - If you use pubkeys file, you can change it without having to restart the watcher.
    - If you use Web3Signer, a call to Web3Signer will be done at every slot to get the
    latest keys to watch.

    \b
    Three prometheus probes are exposed:
    - A missed block proposals counter of your keys
    - The rate of non optimal attestation inclusion of your keys for a given slot
    - The number of two non optimal attestation inclusion in a raw of your keys

    Prometheus server is automatically exposed on port 8000.
    """
    default_set: set[str] = set()

    web3signer_urls = set(web3signer_url) if web3signer_url is not None else default_set
    start_http_server(8000)

    missed_block_proposals_counter = Counter(
        prometheus_probe_missed_block_proposals,
        "Ethereum validator watcher missed block proposals",
    )

    rate_of_not_optimal_attestation_inclusion_gauge = Gauge(
        prometheus_probe_rate_of_not_optimal_attestation_inclusion,
        "Ethereum validator watcher rate of not optimal attestation inclusion",
    )

    number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge = Gauge(
        prometheus_probe_number_of_two_not_optimal_attestation_inclusion_in_a_raw,
        (
            "Ethereum validator watcher number of keys with two not optimal "
            "attestation inclusion in a raw"
        ),
    )

    beacon = Beacon(beacon_url)
    web3signers = {Web3Signer(web3signer_url) for web3signer_url in web3signer_urls}

    previous_slot_number: Optional[int] = None
    previous_epoch: Optional[int] = None
    our_pubkeys: Optional[set[str]] = None

    # Dict containing, for our active validators:
    # - key  : Validator index
    # - value: Validator pubkey
    our_active_val_index_to_pubkey: Optional[dict[int, str]] = None

    # Indexes of our validators which not optimal attestation inclusion for the last
    # epoch
    our_ko_vals_index: set[int] = set()

    # Indexes of our validators which not optimal attestation inclusion for the two last
    # epochs
    our_2_times_in_a_raw_ko_vals_index: set[int] = set()

    for event in sseclient.SSEClient(
        requests.get(
            f"{beacon_url}/eth/v1/events",
            stream=True,
            params=dict(topics="block"),
            headers={"Accept": "text/event-stream"},
        )
    ).events():
        data_dict = json.loads(event.data)
        data_block = DataBlock(**data_dict)

        # This sleep is here to ensure the beacon will respond correctly to all calls
        # relative to the current slot. (Lighthouse ticket to be created)
        time.sleep(1)

        # Retrieve our pubkeys from file and/or Web3Signer
        our_pubkeys = get_our_pubkeys(
            pubkeys_file_path, web3signers, our_pubkeys, data_block.slot
        )

        previous_slot_number = handle_missed_block_detection(
            beacon,
            data_block,
            previous_slot_number,
            missed_block_proposals_counter,
            our_pubkeys,
        )

        previous_epoch = handle_next_blocks_proposal(
            beacon, our_pubkeys, data_block, previous_epoch
        )

        (
            our_active_val_index_to_pubkey,
            our_ko_vals_index,
            our_2_times_in_a_raw_ko_vals_index,
        ) = handle_missed_attestation_detection(
            beacon,
            data_block,
            our_pubkeys,
            our_active_val_index_to_pubkey,
            our_ko_vals_index,
            our_2_times_in_a_raw_ko_vals_index,
            number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge,
            rate_of_not_optimal_attestation_inclusion_gauge,
        )

        if liveliness_file is not None:
            write_liveliness_file(liveliness_file)
