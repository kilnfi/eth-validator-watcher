"""Contains the Beacon class which is used to interact with the consensus layer node."""


import functools
from collections import defaultdict
from functools import lru_cache
from typing import Any, Optional, Union

from requests import HTTPError, Response, Session, codes
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import ChunkedEncodingError, RetryError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from .models import (
    BeaconType,
    Block,
    BlockIdentierType,
    Committees,
    Genesis,
    Header,
    ProposerDuties,
    Rewards,
    Validators,
    ValidatorsLivenessRequestLighthouse,
    ValidatorsLivenessRequestTeku,
    ValidatorsLivenessResponse,
)

StatusEnum = Validators.DataItem.StatusEnum


# Hard-coded for now, will need to move this to a config.
TIMEOUT_BEACON_SEC = 90


print = functools.partial(print, flush=True)


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
        self.__http_retry_not_found = Session()
        self.__http = Session()
        self.__first_liveness_call = True
        self.__first_rewards_call = True

        adapter_retry_not_found = HTTPAdapter(
            max_retries=Retry(
                backoff_factor=0.5,
                total=3,
                status_forcelist=[
                    codes.not_found,
                    codes.bad_gateway,
                    codes.service_unavailable,
                ],
            )
        )

        adapter = HTTPAdapter(
            max_retries=Retry(
                backoff_factor=0.5,
                total=3,
                status_forcelist=[
                    codes.bad_gateway,
                    codes.service_unavailable,
                ],
            )
        )

        self.__http_retry_not_found.mount("http://", adapter_retry_not_found)
        self.__http_retry_not_found.mount("https://", adapter_retry_not_found)

        self.__http.mount("http://", adapter)
        self.__http.mount("https://", adapter)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(ChunkedEncodingError),
    )
    def __get_retry_not_found(self, *args: Any, **kwargs: Any) -> Response:
        """Wrapper around requests.get() with retry on 404"""
        return self.__http_retry_not_found.get(*args, **kwargs)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(ChunkedEncodingError),
    )
    def __get(self, *args: Any, **kwargs: Any) -> Response:
        """Wrapper around requests.get()"""
        return self.__http.get(*args, **kwargs)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(ChunkedEncodingError),
    )
    def __post_retry_not_found(self, *args: Any, **kwargs: Any) -> Response:
        """Wrapper around requests.get() with retry on 404"""
        return self.__http_retry_not_found.post(*args, **kwargs)

    def get_genesis(self) -> Genesis:
        """Get genesis data."""
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/beacon/genesis", timeout=TIMEOUT_BEACON_SEC
        )
        response.raise_for_status()
        genesis_dict = response.json()
        return Genesis(**genesis_dict)

    def get_header(self, block_identifier: Union[BlockIdentierType, int]) -> Header:
        """Get a header.

        Parameters
        block_identifier: Block identifier or slot corresponding to the block to
                          retrieve
        """
        try:
            response = self.__get(
                f"{self.__url}/eth/v1/beacon/headers/{block_identifier}", timeout=TIMEOUT_BEACON_SEC
            )

            response.raise_for_status()

        except HTTPError as e:
            if e.response.status_code == codes.not_found:
                # If we are here, it means the block does not exist
                raise NoBlockError from e

            # If we are here, it's an other error
            raise

        header_dict = response.json()
        return Header(**header_dict)

    def get_block(self, slot: int) -> Block:
        """Get a block.

        Parameters
        slot: Slot corresponding to the block to retrieve
        """
        try:
            response = self.__get(
                f"{self.__url}/eth/v2/beacon/blocks/{slot}", timeout=TIMEOUT_BEACON_SEC
            )

            response.raise_for_status()

        except HTTPError as e:
            if e.response.status_code == codes.not_found:
                # If we are here, it means the block does not exist
                raise NoBlockError from e

            # If we are here, it's an other error
            raise

        block_dict = response.json()
        return Block(**block_dict)

    @lru_cache()
    def get_proposer_duties(self, epoch: int) -> ProposerDuties:
        """Get proposer duties

        epoch: Epoch corresponding to the proposer duties to retrieve
        """
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/validator/duties/proposer/{epoch}", timeout=TIMEOUT_BEACON_SEC
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
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/beacon/states/head/validators", timeout=TIMEOUT_BEACON_SEC
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
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/beacon/states/head/committees",
            params=dict(epoch=epoch),
            timeout=TIMEOUT_BEACON_SEC,
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

    def get_rewards(
        self,
        beacon_type: BeaconType,
        epoch: int,
        validators_index: set[int] | None = None,
    ) -> Rewards:
        """Get rewards.

        Parameters:
        beacon_type     : Type of beacon node
        epoch           : Epoch corresponding to the rewards to retrieve
        validators_index: Set of validator indexes corresponding to the rewards to
                          retrieve. If None, rewards for all validators will be
                          retrieved.
        """

        # On Prysm, because of
        # https://github.com/prysmaticlabs/prysm/issues/11581,
        # we just assume there is no rewards at all

        # On Nimbus, because of
        # https://github.com/status-im/nimbus-eth2/issues/5138,
        # we just assume there is no rewards at all

        if beacon_type in {BeaconType.NIMBUS, BeaconType.OLD_PRYSM}:
            if self.__first_rewards_call:
                self.__first_rewards_call = False
                print(
                    (
                        "⚠️ You are using Prysm < 4.0.8 or Nimbus. Rewards will be "
                        "ignored. See "
                        "https://github.com/prysmaticlabs/prysm/issues/11581 "
                        "(Prysm) & https://github.com/status-im/nimbus-eth2/issues/5138 "
                        "(Nimbus) for more information."
                    )
                )

            return Rewards(data=Rewards.Data(ideal_rewards=[], total_rewards=[]))

        response = self.__post_retry_not_found(
            f"{self.__url}/eth/v1/beacon/rewards/attestations/{epoch}",
            json=(
                [str(index) for index in sorted(validators_index)]
                if validators_index is not None
                else []
            ),
            timeout=TIMEOUT_BEACON_SEC,
        )

        response.raise_for_status()
        rewards_dict = response.json()
        return Rewards(**rewards_dict)

    def get_validators_liveness(
        self, beacon_type: BeaconType, epoch: int, validators_index: set[int]
    ) -> dict[int, bool]:
        """Get validators liveness.

        Parameters      :
        beacon_type     : Type of beacon node
        epoch           : Epoch corresponding to the validators liveness to retrieve
        validators_index: Set of validator indexs corresponding to the liveness to
                          retrieve
        """

        # On Nimbus, because of
        # https://github.com/status-im/nimbus-eth2/issues/5019,
        # we just assume that all validators are live

        if beacon_type == BeaconType.NIMBUS:
            if self.__first_liveness_call:
                self.__first_liveness_call = False
                print(
                    (
                        "⚠️ You are using Nimbus. Missed attestations will be ignored. "
                        "See https://github.com/status-im/nimbus-eth2/issues/5019 for "
                        "more information."
                    )
                )

            return {index: True for index in validators_index}

        beacon_type_to_function = {
            BeaconType.LIGHTHOUSE: self.__get_validators_liveness_lighthouse,
            BeaconType.OLD_PRYSM: self.__get_validators_liveness_beacon_api,
            BeaconType.OLD_TEKU: self.__get_validators_liveness_old_teku,
            BeaconType.OTHER: self.__get_validators_liveness_beacon_api,
        }

        response = beacon_type_to_function[beacon_type](epoch, validators_index)

        try:
            response.raise_for_status()
        except HTTPError as e:
            if e.response.status_code != codes.bad_request:
                raise

            # If we are here, it means the requested epoch is too old, which
            # could be normal if the watcher just started
            print(
                f"❓     Missed attestations detection is disabled for epoch {epoch}. "
            )

            print(
                "❓     You can ignore this message if the watcher just started less "
                "than one epoch ago. Otherwise, please check that you used the correct "
                f"`beacon_type` option (currently set to `{beacon_type}`). "
            )

            return {index: True for index in validators_index}

        validators_liveness_dict = response.json()
        validators_liveness = ValidatorsLivenessResponse(**validators_liveness_dict)

        return {item.index: item.is_live for item in validators_liveness.data}

    def get_potential_block(self, slot) -> Block | None:
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
        return self.__post_retry_not_found(
            f"{self.__url}/lighthouse/liveness",
            json=ValidatorsLivenessRequestLighthouse(
                epoch=epoch, indices=sorted(list(validators_index))
            ).model_dump(),
            timeout=TIMEOUT_BEACON_SEC,
        )

    def __get_validators_liveness_old_teku(
        self, epoch: int, validators_index: set[int]
    ) -> Response:
        """Get validators liveness from Teku.

        https://github.com/ConsenSys/teku/issues/7204

        Parameters:
        epoch           : Epoch corresponding to the validators liveness to retrieve
        validators_index: Set of validator indexs corresponding to the liveness to
                          retrieve
        """
        return self.__post_retry_not_found(
            f"{self.__url}/eth/v1/validator/liveness/{epoch}",
            json=ValidatorsLivenessRequestTeku(
                indices=sorted(list(validators_index))
            ).model_dump(),
            timeout=TIMEOUT_BEACON_SEC,
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
        return self.__post_retry_not_found(
            f"{self.__url}/eth/v1/validator/liveness/{epoch}",
            json=[
                str(validator_index)
                for validator_index in sorted(list(validators_index))
            ],
            timeout=TIMEOUT_BEACON_SEC,
        )
