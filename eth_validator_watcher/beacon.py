from collections import defaultdict
from functools import lru_cache
from typing import Optional
from prometheus_client import Gauge

from requests import Session, codes
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RetryError

from .models import (
    Block,
    Committees,
    ProposerDuties,
    Validators,
    ValidatorsLivenessRequest,
    ValidatorsLivenessResponse,
)
from .utils import (
    aggregate_bools,
    convert_hex_to_bools,
    remove_all_items_from_last_true,
    switch_endianness,
)

our_active_validators_count = Gauge(
    "our_active_validators_count",
    "Our active validators count",
)

our_pending_validators_count = Gauge(
    "our_pending_validators_count",
    "Our pending validators count",
)

total_active_validators_count = Gauge(
    "total_active_validators_count",
    "Total active validators count",
)


class NoBlockError(Exception):
    pass


class Beacon:
    def __init__(self, url: str) -> None:
        """Beacon

        url: URL where the beacon can be reached
        """
        self.__url = url
        self.__http = Session()

        self.__http.mount(
            "http://",
            HTTPAdapter(
                max_retries=Retry(
                    backoff_factor=0.5,
                    total=3,
                    status_forcelist=[codes.not_found],
                )
            ),
        )

    def get_block(self, slot: int) -> Block:
        """Get a block

        slot: Slot
        """
        try:
            response = self.__http.get(f"{self.__url}/eth/v2/beacon/blocks/{slot}")
        except RetryError as e:
            # If we are here, it means the block does not exist
            raise NoBlockError from e

        response.raise_for_status()

        block_dict = response.json()
        return Block(**block_dict)

    @lru_cache(maxsize=2)
    def get_proposer_duties(self, epoch: int) -> ProposerDuties:
        """Get proposer duties

        epoch: Epoch
        """
        response = self.__http.get(
            f"{self.__url}/eth/v1/validator/duties/proposer/{epoch}"
        )

        response.raise_for_status()

        proposer_duties_dict = response.json()
        return ProposerDuties(**proposer_duties_dict)

    def get_active_index_to_pubkey(self, pubkeys: set[str]) -> dict[int, str]:
        """Return a dictionnary with:
        key  : Index of validator
        value: Public key for validator

        pubkeys: The set of validators pubkey to use.
        """
        response = self.__http.get(
            f"{self.__url}/eth/v1/beacon/states/head/validators",
            params=dict(status=Validators.DataItem.StatusEnum.active),
        )

        response.raise_for_status()
        validators_dict = response.json()
        validators = Validators(**validators_dict)

        total_active_validators_count.set(len(validators.data))

        our_active_index_to_pubkey = {
            item.index: item.validator.pubkey
            for item in validators.data
            if item.validator.pubkey in pubkeys
        }

        our_active_validators_count.set(len(our_active_index_to_pubkey))

        return our_active_index_to_pubkey

    def get_pending_index_to_pubkey(self, pubkeys: set[str]) -> dict[int, str]:
        """Return a dictionnary with:
        key  : Index of validator
        value: Public key for validator

        pubkeys: The set of validators pubkey to use.
        """
        response = self.__http.get(
            f"{self.__url}/eth/v1/beacon/states/head/validators",
            params=dict(status=Validators.DataItem.StatusEnum.pending),
        )

        response.raise_for_status()
        validators_dict = response.json()
        validators = Validators(**validators_dict)

        our_pending_index_to_pubkey = {
            item.index: item.validator.pubkey
            for item in validators.data
            if item.validator.pubkey in pubkeys
        }

        our_pending_validators_count.set(len(our_pending_index_to_pubkey))

        return our_pending_index_to_pubkey

    @lru_cache(maxsize=1)
    def get_duty_slot_to_committee_index_to_validators_index(
        self, epoch: int
    ) -> dict[int, dict[int, list[int]]]:
        """Return a nested dictionnary.
        outer key               : Slot number
        outer value (=inner key): Committee index
        inner value             : Index of validators which have to attest in the
                                  given committee index at the given slot

        epoch: Epoch
        """
        response = self.__http.get(
            f"{self.__url}/eth/v1/beacon/states/head/committees",
            params=dict(epoch=epoch),
        )

        response.raise_for_status()
        committees_dict = response.json()

        committees = Committees(**committees_dict)
        data = committees.data

        # TODO: Do it with dict comprehension
        result: dict[int, dict[int, list[int]]] = defaultdict(dict)

        for item in data:
            result[item.slot][item.index] = item.validators

        return result

    def get_validators_liveness(
        self, epoch: int, validators_index: set[int]
    ) -> dict[int, bool]:
        response = self.__http.post(
            f"{self.__url}/lighthouse/liveness",
            json=ValidatorsLivenessRequest(
                epoch=epoch, indices=sorted(list(validators_index))
            ).dict(),
        )

        response.raise_for_status()
        validators_liveness_dict = response.json()
        validators_liveness = ValidatorsLivenessResponse(**validators_liveness_dict)

        return {item.index: item.is_live for item in validators_liveness.data}

    def get_potential_block(self, slot) -> Optional[Block]:
        try:
            return self.get_block(slot)
        except NoBlockError:
            # The block is probably orphaned:
            # The beacon saw the block (that's why we received the event) but it was
            # orphaned before we could fetch it.
            return None
