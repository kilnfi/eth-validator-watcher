"""Contains function to handle next blocks proposal"""

import functools

from prometheus_client import Gauge

from .beacon import Beacon
from .utils import NB_SLOT_PER_EPOCH

print = functools.partial(print, flush=True)

metric_future_block_proposals_count = Gauge(
    "future_block_proposals_count",
    "Future block proposals count",
)

metric_future_block_proposals = Gauge(
    "future_block_proposals",
    "Future block proposals",
    ["pubkey","index", "slot", "epoch", "deployment_id", "validator_id"]
)


def process_future_blocks_proposal(
    beacon: Beacon,
    our_validators: dict[str, tuple[str, str]],
    slot: int,
    is_new_epoch: bool,
) -> int:
    """Handle next blocks proposal

    Parameters:
    beacon      : Beacon
    our_validators : A dictionary with public keys as keys and a tuple with the deployment_id and the validator_id as values
    slot        : Slot
    is_new_epoch: Is new epoch
    """
    epoch = slot // NB_SLOT_PER_EPOCH
    proposers_duties_current_epoch = beacon.get_proposer_duties(epoch)
    proposers_duties_next_epoch = beacon.get_proposer_duties(epoch + 1)

    concatenated_data = (
        proposers_duties_current_epoch.data + proposers_duties_next_epoch.data
    )

    filtered = [
        item
        for item in concatenated_data
        if item.pubkey in our_validators.keys() and item.slot >= slot
    ]
    
    metric_future_block_proposals_count.set(len(filtered))

    for item in filtered:
        metric_future_block_proposals.labels(
            pubkey=item.pubkey,
            index=item.validator_index,
            slot=item.slot,
            epoch=epoch,
            deployment_id=our_validators[item.pubkey][0],
            validator_id=our_validators[item.pubkey][1]
        ).set(1)

    if is_new_epoch:
        for item in filtered:
            print(
                f"💍 Our validator {item.pubkey[:10]} is going to propose a block "
                f"at   slot {item.slot} (in {item.slot - slot} slots)"
            )

    return len(filtered)
