"""Contains functions to handle missed block proposals detection"""

import functools
from typing import Optional

from prometheus_client import Counter

from .beacon import Beacon
from .models import Block
from .utils import NB_SLOT_PER_EPOCH, Slack

print = functools.partial(print, flush=True)

missed_block_proposals_count = Counter(
    "missed_block_proposals_count",
    "Missed block proposals count",
)
missed_block_proposals_count_details = Counter(
    "missed_block_proposals_count_details",
    "Missed block proposals count_details",
    ["slot", "epoch"],
)

proposed_block_proposals_count = Counter(
    "proposed_block_proposals_count",
    "Proposed block proposals count",
)

proposed_block_proposals_count_details = Counter(
    "proposed_block_proposals_count_details",
    "Proposed block proposals count_details",
    ["slot", "epoch"],
)

key_missed_block_proposals_count = Counter(
    "key_missed_block_proposals_count",
    "Key missed block proposals count",
    ["pubkey"],
)

key_missed_block_proposals_count_details = Counter(
    "key_missed_block_proposals_count_details",
    "Key missed block proposals count_details",
    ["pubkey", "slot", "epoch"],
)

key_proposed_block_proposals_count = Counter(
    "key_proposed_block_proposals_count",
    "Key proposed block proposals count",
    ["pubkey"],
)

key_proposed_block_proposals_count_details = Counter(
    "key_proposed_block_proposals_count_details",
    "Key proposed block proposals count_details",
    ["pubkey", "slot", "epoch"],
)

initialized_keys: set[str] = set()


def process_missed_blocks(
    beacon: Beacon,
    potential_block: Optional[Block],
    slot: int,
    our_pubkeys: set[str],
    slack: Optional[Slack],
) -> bool:
    """Process missed block proposals detection

    Parameters:
    beacon         : Beacon
    potential_block: Potential block
    slot           : Slot
    our_pubkeys    : Set of our validators public keys
    slack          : Slack instance

    Returns `True` if we had to propose the block, `False` otherwise
    """

    for _key in our_pubkeys:
        if _key not in initialized_keys:
            key_missed_block_proposals_count.labels(pubkey=_key)
            key_proposed_block_proposals_count.labels(pubkey=_key)
            initialized_keys.add(_key)
    for _key in initialized_keys:
        if _key not in our_pubkeys:
            key_missed_block_proposals_count.remove(pubkey=_key)
            key_missed_block_proposals_count_details.remove(pubkey=_key)
            key_proposed_block_proposals_count.remove(pubkey=_key)
            key_proposed_block_proposals_count_details.remove(pubkey=_key)
            initialized_keys.remove(_key)

    missed = potential_block is None
    epoch = slot // NB_SLOT_PER_EPOCH
    proposer_duties = beacon.get_proposer_duties(epoch)

    # Get proposer public key for this slot
    proposer_duties_data = proposer_duties.data

    # In `data` list, items seem to be ordered by slot.
    # However, there is no specification for that, so it is wiser to
    # iterate on the list
    proposer_pubkey = next(
        (
            proposer_duty_data.pubkey
            for proposer_duty_data in proposer_duties_data
            if proposer_duty_data.slot == slot
        )
    )

    # Check if the validator that has to propose is ours
    is_our_validator = proposer_pubkey in our_pubkeys
    positive_emoji = "✨" if is_our_validator else "✅"
    negative_emoji = "❌" if is_our_validator else "💩"

    emoji, proposed_or_missed = (
        (negative_emoji, "missed  ") if missed else (positive_emoji, "proposed")
    )

    short_proposer_pubkey = proposer_pubkey[:10]

    message_console = (
        f"{emoji} {'Our ' if is_our_validator else '    '}validator "
        f"{short_proposer_pubkey} {proposed_or_missed} block at epoch {epoch} - "
        f"slot {slot} {emoji} - 🔑 {len(our_pubkeys)} keys "
        "watched"
    )

    print(message_console)

    if slack is not None and missed and is_our_validator:
        message_slack = (
            f"{emoji} {'Our ' if is_our_validator else '    '}validator "
            f"`{short_proposer_pubkey}` {proposed_or_missed} block at epoch `{epoch}` - "
            f"slot `{slot}` {emoji}"
        )

        slack.send_message(message_slack)

    if is_our_validator and missed:
        missed_block_proposals_count.inc()
        missed_block_proposals_count_details.labels(slot=slot, epoch=epoch).inc()

        key_missed_block_proposals_count.labels(pubkey=proposer_pubkey).inc()
        key_missed_block_proposals_count_details.labels(
            pubkey=proposer_pubkey, slot=slot, epoch=epoch
        ).inc()
    elif is_our_validator and not missed:
        proposed_block_proposals_count.inc()
        proposed_block_proposals_count_details.labels(slot=slot, epoch=epoch).inc()

        key_proposed_block_proposals_count.labels(pubkey=proposer_pubkey).inc()
        key_proposed_block_proposals_count_details.labels(
            pubkey=proposer_pubkey, slot=slot, epoch=epoch
        ).inc()

    return is_our_validator
