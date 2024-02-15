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


def process_future_blocks_proposal(
    beacon: Beacon,
    our_pubkeys: set[str],
    slot: int,
    is_new_epoch: bool,
    slots_per_epoch: int = NB_SLOT_PER_EPOCH,
) -> int:
    """Handle next blocks proposal

    Parameters:
    beacon      : Beacon
    our_pubkeys : Set of our validators public keys
    slot        : Slot
    is_new_epoch: Is new epoch
    """
    epoch = slot // slots_per_epoch
    proposers_duties_current_epoch = beacon.get_proposer_duties(epoch)
    proposers_duties_next_epoch = beacon.get_proposer_duties(epoch + 1)

    concatenated_data = (
        proposers_duties_current_epoch.data + proposers_duties_next_epoch.data
    )

    filtered = [
        item
        for item in concatenated_data
        if item.pubkey in our_pubkeys and item.slot >= slot
    ]

    metric_future_block_proposals_count.set(len(filtered))

    if is_new_epoch:
        for item in filtered:
            print(
                f"💍 Our validator {item.pubkey[:10]} is going to propose a block "
                f"at   slot {item.slot} (in {item.slot - slot} slots)"
            )

    return len(filtered)
