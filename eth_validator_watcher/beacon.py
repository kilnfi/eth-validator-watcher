"""Contains the Beacon class which is used to interact with the consensus layer node."""


from collections import defaultdict
from functools import lru_cache
from typing import Optional

from requests import Response, Session, codes
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RetryError

from .models import (
    BeaconType,
    Block,
    Committees,
    Genesis,
    ProposerDuties,
    Validators,
    ValidatorsLivenessRequestLighthouse,
    ValidatorsLivenessRequestTeku,
    ValidatorsLivenessResponse,
)

StatusEnum = Validators.DataItem.StatusEnum


class NoBlockError(Exception):
    pass


class Beacon:
    """Beacon node abstraction."""

    def __init__(self, url: str) -> None:
        """Beacon

        Parameters:
        url: URL where the beacon can be reached
        """
        self.__url = url
        self.__http = Session()
        self.__nimbus_first_liveness_call = False

        adapter = HTTPAdapter(
            max_retries=Retry(
                backoff_factor=0.5,
                total=3,
                status_forcelist=[codes.not_found],
            )
        )

        self.__http.mount("http://", adapter)
        self.__http.mount("https://", adapter)

    def get_genesis(self) -> Genesis:
        """Get genesis data."""
        response = self.__http.get(f"{self.__url}/eth/v1/beacon/genesis")
        response.raise_for_status()
        genesis_dict = response.json()
        return Genesis(**genesis_dict)

    def get_block(self, slot: int) -> Block:
        """Get a block.

        Parameters
        slot: Slot corresponding to the block to retrieve
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

        epoch: Epoch corresponding to the proposer duties to retrieve
        """
        response = self.__http.get(
            f"{self.__url}/eth/v1/validator/duties/proposer/{epoch}"
        )

        response.raise_for_status()

        proposer_duties_dict = response.json()
        return ProposerDuties(**proposer_duties_dict)

    def get_status_to_index_to_validator(
        self,
    ) -> dict[StatusEnum, dict[int, Validators.DataItem.Validator]]:
        """Get a nested dictionnary with:
        outer key               : Status
        outer value (=inner key): Index of validator
        inner value             : Validator
        """
        response = self.__http.get(
            f"{self.__url}/eth/v1/beacon/states/head/validators",
        )

        response.raise_for_status()
        validators_dict = response.json()

        validators = Validators(**validators_dict)

        result: dict[
            StatusEnum, dict[int, Validators.DataItem.Validator]
        ] = defaultdict(dict)

        for item in validators.data:
            result[item.status][item.index] = item.validator

        return result

    @lru_cache(maxsize=1)
    def get_duty_slot_to_committee_index_to_validators_index(
        self, epoch: int
    ) -> dict[int, dict[int, list[int]]]:
        """Get a nested dictionnary.
        outer key               : Slot number
        outer value (=inner key): Committee index
        inner value             : Index of validators that have to attest in the
                                  given committee index at the given slot

        Parameters:
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
        self, beacon_type: BeaconType, epoch: int, validators_index: set[int]
    ) -> dict[int, bool]:
        """Get validators liveness.

        Parameters      :
        beacon_type     : Type of beacon node (Teku, Lighthouse or other)
        epoch           : Epoch corresponding to the validators liveness to retrieve
        validators_index: Set of validator indexs corresponding to the liveness to
                          retrieve
        """

        # On Nimbus, because of
        # https://github.com/status-im/nimbus-eth2/issues/5019,
        # we just assume that all validators are live

        if beacon_type == BeaconType.NIMBUS:
            if not self.__nimbus_first_liveness_call:
                self.__nimbus_first_liveness_call = True
                print(
                    (
                        "⚠️ You are using Nimbus. Liveness will be ignored. "
                        "See https://github.com/status-im/nimbus-eth2/issues/5019 for "
                        "more information."
                    )
                )

            return {index: True for index in validators_index}

        beacon_type_to_function = {
            BeaconType.LIGHTHOUSE: self.__get_validators_liveness_lighthouse,
            BeaconType.TEKU: self.__get_validators_liveness_teku,
            BeaconType.OTHER: self.__get_validators_liveness_beacon_api,
        }

        response = beacon_type_to_function[beacon_type](epoch, validators_index)

        response.raise_for_status()
        validators_liveness_dict = response.json()
        validators_liveness = ValidatorsLivenessResponse(**validators_liveness_dict)

        return {item.index: item.is_live for item in validators_liveness.data}

    def get_potential_block(self, slot) -> Optional[Block]:
        """Get a block if it exists, otherwise return None.

        Parameters:
        slot: Slot corresponding to the block to retrieve
        """
        try:
            return self.get_block(slot)
        except NoBlockError:
            # The block is probably orphaned:
            # The beacon saw the block (that's why we received the event) but it was
            # orphaned before we could fetch it.
            return None

    def __get_validators_liveness_lighthouse(
        self, epoch: int, validators_index: set[int]
    ) -> Response:
        """Get validators liveness from Lighthouse.

        https://github.com/sigp/lighthouse/issues/4243

        Parameters:
        epoch           : Epoch corresponding to the validators liveness to retrieve
        validators_index: Set of validator indexs corresponding to the liveness to
                          retrieve
        """
        return self.__http.post(
            f"{self.__url}/lighthouse/liveness",
            json=ValidatorsLivenessRequestLighthouse(
                epoch=epoch, indices=sorted(list(validators_index))
            ).model_dump(),
        )

    def __get_validators_liveness_teku(
        self, epoch: int, validators_index: set[int]
    ) -> Response:
        """Get validators liveness from Teku.

        https://github.com/ConsenSys/teku/issues/7204

        Parameters:
        epoch           : Epoch corresponding to the validators liveness to retrieve
        validators_index: Set of validator indexs corresponding to the liveness to
                          retrieve
        """
        return self.__http.post(
            f"{self.__url}/eth/v1/validator/liveness/{epoch}",
            json=ValidatorsLivenessRequestTeku(
                indices=sorted(list(validators_index))
            ).model_dump(),
        )

    def __get_validators_liveness_beacon_api(
        self, epoch: int, validators_index: set[int]
    ) -> Response:
        """Get validators liveness from neither Lighthouse nor Teku.

        https://github.com/ConsenSys/teku/issues/7204

        Parameters:
        epoch           : Epoch corresponding to the validators liveness to retrieve
        validators_index: Set of validator indexs corresponding to the liveness to
                          retrieve
        """
        return self.__http.post(
            f"{self.__url}/eth/v1/validator/liveness/{epoch}",
            json=[
                str(validator_index)
                for validator_index in sorted(list(validators_index))
            ],
        )
