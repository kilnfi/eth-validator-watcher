"""Contains the logic to check if the fee recipient is the one expected."""


from prometheus_client import Counter

from .execution import Execution
from .models import Block, Validators
from .utils import NB_SLOT_PER_EPOCH, Slack

metric_wrong_fee_recipient_proposed_block_count = Counter(
    "wrong_fee_recipient_proposed_block_count",
    "Wrong fee recipient proposed block count",
)


def process_fee_recipient(
    block: Block,
    index_to_validator: dict[int, Validators.DataItem.Validator],
    execution: Execution | None,
    expected_fee_recipient: str | None,
    slack: Slack | None,
) -> None:
    """Check if the fee recipient is the one expected.

    Parameters:
    block                 : The block to check against the fee recipient
    index_to_validator    : Dictionary with:
        key  : validator index
        value: validator data corresponding to the validator index
    execution             : Optional execution client
    expected_fee_recipient: The expected fee recipient
    slack                 : Optional slack client
    """

    # No expected fee recipient set, nothing to do
    if execution is None or expected_fee_recipient is None:
        return

    proposer_index = block.data.message.proposer_index

    # Not our validator, nothing to do
    if proposer_index not in index_to_validator:
        return

    short_proposer_pubkey = index_to_validator[proposer_index].pubkey[:10]
    slot = block.data.message.slot
    epoch = slot // NB_SLOT_PER_EPOCH

    # First, we check if the beacon block fee recipient is the one expected
    # `.lower()` is here just in case the execution client returns a fee recipient in
    # checksum casing
    actual_fee_recipient = (
        block.data.message.body.execution_payload.fee_recipient.lower()
    )

    if actual_fee_recipient == expected_fee_recipient:
        # Allright, we're good
        return

    # If not, it may be because the block was built by an external builder that
    # set its own fee recipient. In this case, we need to check if the last transaction
    # in the execution block is a transaction to the expected fee recipient.

    execution_block_hash = block.data.message.body.execution_payload.block_hash
    execution_block = execution.eth_get_block_by_hash(execution_block_hash)
    transactions = execution_block.result.transactions

    try:
        *_, last_transaction = transactions

        # `.lower()` is here just in case the execution client returns transacion "to"
        # in checksum casing

        if (
            last_transaction.to is not None
            and expected_fee_recipient == last_transaction.to.lower()
        ):
            # The last transaction is to the expected fee recipient
            return
    except ValueError:
        # The block is empty, so we can't check the last transaction
        pass

    # If we are here, it means that the fee recipient is wrong
    message = (
        f"🚩 Our validator {short_proposer_pubkey} "
        f"proposed block at epoch {epoch} - slot {slot} "
        "with the wrong fee recipient"
    )

    print(message)

    if slack is not None:
        slack.send_message(message)

    metric_wrong_fee_recipient_proposed_block_count.inc()
