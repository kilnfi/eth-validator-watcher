from enum import Enum

from pydantic import BaseModel


class Validators(BaseModel):
    class DataItem(BaseModel):
        class StatusEnum(str, Enum):
            pendingInitialized = "pending_initialized"
            pendingQueued = "pending_queued"
            activeOngoing = "active_ongoing"
            activeExiting = "active_exiting"
            activeSlashed = "active_slashed"
            exitedUnslashed = "exited_unslashed"
            exitedSlashed = "exited_slashed"
            withdrawalPossible = "withdrawal_possible"
            withdrawalDone = "withdrawal_done"

            active = "active"
            pending = "pending"
            exited = "exited"
            withdrawal = "withdrawal"

        class Validator(BaseModel):
            pubkey: str

        index: int
        status: StatusEnum

        validator: Validator

    data: list[DataItem]


class Block(BaseModel):
    class Data(BaseModel):
        class Message(BaseModel):
            class Body(BaseModel):
                class Eth1Data(BaseModel):
                    deposit_root: str
                    deposit_count: int
                    block_hash: str

                class Attestation(BaseModel):
                    class Data(BaseModel):
                        class Source(BaseModel):
                            epoch: int
                            root: str

                        class Target(BaseModel):
                            epoch: int
                            root: str

                        slot: int
                        index: int
                        beacon_block_root: str
                        source: Source
                        target: Target

                    aggregation_bits: str
                    data: Data
                    signature: str

                randao_reveal: str
                eth1_data: Eth1Data
                graffiti: str
                proposer_slashings: list[int]
                attester_slashings: list[int]
                attestations: list[Attestation]

            slot: int
            proposer_index: int
            parent_root: str
            state_root: str
            body: Body

        message: Message

    version: str
    execution_optimistic: bool
    data: Data


class EventBlock(BaseModel):
    slot: int


class Committees(BaseModel):
    class Data(BaseModel):
        index: int
        slot: int
        validators: list[int]

    execution_optimistic: bool
    data: list[Data]


class ProposerDuties(BaseModel):
    class Data(BaseModel):
        pubkey: str
        validator_index: int
        slot: int

    dependent_root: str
    data: list[Data]


class ValidatorsLivenessRequest(BaseModel):
    indices: list[int]
    epoch: int


class ValidatorsLivenessResponse(BaseModel):
    class Data(BaseModel):
        index: int
        epoch: int
        is_live: bool

    data: list[Data]


class SlotWithStatus(BaseModel):
    number: int
    missed: bool


class CoinbaseTrade(BaseModel):
    time: str
    trade_id: int
    price: float
    size: float
    side: str
