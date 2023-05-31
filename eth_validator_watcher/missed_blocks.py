import functools
from typing import Optional

from prometheus_client import Counter

from .beacon import Beacon
from .models import Block
from .utils import NB_SLOT_PER_EPOCH, Slack

print = functools.partial(print, flush=True)

missed_block_proposals_count = Counter(
    "missed_block_proposals_count",
    "Missed block proposals_count",
)


def process_missed_blocks(
    beacon: Beacon,
    potential_block: Optional[Block],
    slot: int,
    our_pubkeys: set[str],
    slack: Optional[Slack],
) -> None:
    """Handle missed block proposals detection

    Print log each time a block is proposed.
    Update prometheus probe for our public keys which did not proposed a block

    Returns the current slot.

    beacon                        : Beacon
    slot                          : Slot
    previous_slot                 : Previous slot (Optional)
    missed_block_proposals_counter: Prometheus counter
    our_pubkeys                   : Set of our validators public keys
    """
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
