from typing import Optional

from .beacon import Beacon
from .models import DataBlock
from .utils import NB_SLOT_PER_EPOCH


def handle_next_blocks_proposal(
    beacon: Beacon,
    our_pubkeys: set[str],
    data_block: DataBlock,
    previous_epoch: Optional[int],
) -> int:
    """Handle next blocks proposal

    Print one log for each of our key which is about to propose a block in the next
    two epochs.

    Return the current epoch.

    beacon        : Beacon
    our_pubkeys   : Set of our validators public keys
    data_block    : Data value of a beacon chain block
    previous_epoch: Previous epoch
    """
    slot = data_block.slot
    epoch = slot // NB_SLOT_PER_EPOCH
    next_epoch = epoch + 1

    if our_pubkeys == set() or previous_epoch is not None and epoch == previous_epoch:
        return epoch

    proposers_duties_current_epoch = beacon.get_proposer_duties(epoch)
    proposers_duties_next_epoch = beacon.get_proposer_duties(next_epoch)

    concatenated_data = (
        proposers_duties_current_epoch.data + proposers_duties_next_epoch.data
    )

    for item in concatenated_data:
        if item.pubkey in our_pubkeys and item.slot >= slot:
            print(
                f"💍 Our validator {item.pubkey[:10]} is going to propose a block "
                f"at   slot {item.slot} (in {item.slot - slot} slots)"
            )

    return epoch
