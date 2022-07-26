from pydantic import BaseModel


class DataBlock(BaseModel):
    slot: int
    block: str
    execution_optimistic: bool


class ProposerDuties(BaseModel):
    class Data(BaseModel):
        pubkey: str
        validator_index: int
        slot: int

    dependent_root: str
    data: list[Data]


class SlotWithStatus(BaseModel):
    number: int
    missed: bool
