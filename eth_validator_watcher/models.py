"""Pydantic models for Ethereum validator watcher data structures."""

from enum import StrEnum

from pydantic import BaseModel


class Validators(BaseModel):
    """Model for validator data from the beacon chain.

    Args:
        None

    Returns:
        None
    """
    class DataItem(BaseModel):
        class StatusEnum(StrEnum):
            pendingInitialized = "pending_initialized"
            pendingQueued = "pending_queued"
            activeOngoing = "active_ongoing"
            activeExiting = "active_exiting"
            activeSlashed = "active_slashed"
            exitedUnslashed = "exited_unslashed"
            exitedSlashed = "exited_slashed"
            withdrawalPossible = "withdrawal_possible"
            withdrawalDone = "withdrawal_done"

        class Validator(BaseModel):
            pubkey: str
            effective_balance: int
            slashed: bool
            activation_epoch: int
            withdrawal_credentials: str

        index: int
        status: StatusEnum

        validator: Validator

    data: list[DataItem]


class Genesis(BaseModel):
    """Model for beacon chain genesis data.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        genesis_time: int

    data: Data


class Spec(BaseModel):
    """Model for beacon chain specification data.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        SECONDS_PER_SLOT: int
        SLOTS_PER_EPOCH: int

    data: Data


class Header(BaseModel):
    """Model for block header data from the beacon chain.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        class Header(BaseModel):
            class Message(BaseModel):
                slot: int

            message: Message

        header: Header

    data: Data


class Block(BaseModel):
    """Model for block data from the beacon chain.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        class Message(BaseModel):
            class Body(BaseModel):
                class Attestation(BaseModel):
                    class Data(BaseModel):
                        slot: int
                        index: int

                    aggregation_bits: str
                    data: Data

                class ExecutionPayload(BaseModel):
                    fee_recipient: str
                    block_hash: str

                attestations: list[Attestation]
                execution_payload: ExecutionPayload

            slot: int
            proposer_index: int
            body: Body

        message: Message

    data: Data


class ProposerDuties(BaseModel):
    """Model for validator proposer duties data.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        pubkey: str
        validator_index: int
        slot: int

    dependent_root: str
    data: list[Data]


class ValidatorsLivenessResponse(BaseModel):
    """Model for validator liveness data.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        index: int
        is_live: bool

    data: list[Data]


class SlotWithStatus(BaseModel):
    """Model for slot data with missed status.

    Args:
        None

    Returns:
        None
    """
    number: int
    missed: bool


class CoinbaseTrade(BaseModel):
    """Model for Coinbase trade data.

    Args:
        None

    Returns:
        None
    """
    time: str
    trade_id: int
    price: float
    size: float
    side: str


class BlockIdentierType(StrEnum):
    """Enumeration of block identifier types.

    Args:
        None

    Returns:
        None
    """
    HEAD = "head"
    GENESIS = "genesis"
    FINALIZED = "finalized"


class Rewards(BaseModel):
    """Model for validator reward data.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        class IdealReward(BaseModel):
            effective_balance: int
            source: int
            target: int
            head: int

        class TotalReward(BaseModel):
            validator_index: int
            source: int
            target: int
            head: int

        ideal_rewards: list[IdealReward]
        total_rewards: list[TotalReward]

    data: Data


class Committees(BaseModel):
    """Model for committee assignment data.

    Args:
        None

    Returns:
        None
    """
    class Data(BaseModel):
        index: int
        slot: int
        validators: list[int]

    data: list[Data]


class Attestations(BaseModel):
    """Model for attestation data from blocks.

    Args:
        None

    Returns:
        None
    """
    class SignedAttestationData(BaseModel):
        class AttestationData(BaseModel):
            slot: int

        aggregation_bits: str
        committee_bits: str
        data: AttestationData

    data: list[SignedAttestationData]


class PendingDeposits(BaseModel):
    """Model for pending deposit data.
        Args:
                None
        Returns:
                None
        """

    class PendingDepositData(BaseModel):
        pubkey: str
        withdrawal_credentials: str
        amount: int
        slot: int

    data: list[PendingDepositData]


class PendingConsolidations(BaseModel):
    """Model for pending consolidation data.

    Args:
        None
    Returns:
        None
    """
    class PendingConsolidationData(BaseModel):
        source_index: int
        target_index: int

    data: list[PendingConsolidationData]


class PendingWithdrawals(BaseModel):
    """Model for pending withdrawal data.

    Args:
        None
    Returns:
        None
    """
    class PendingWithdrawalData(BaseModel):
        validator_index: int
        amount: int

    data: list[PendingWithdrawalData]
