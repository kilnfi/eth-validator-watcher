"""Contains the Beacon class which is used to interact with the consensus layer node."""

import functools
from collections import defaultdict
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
    Spec,
    Validators,
    ValidatorsLivenessResponse,
)


StatusEnum = Validators.DataItem.StatusEnum


print = functools.partial(print, flush=True)


class NoBlockError(Exception):
    pass


class Beacon:
    """Beacon node abstraction."""

    def __init__(self, url: str, timeout_sec: int) -> None:
        """Beacon

        Parameters:
        url        : URL where the beacon can be reached
        timeout_sec: timeout in seconds used to query the beacon
        """
        self.__url = url
        self.__timeout_sec = timeout_sec
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

    def get_url(self) -> str:
        """Return the URL of the beacon."""
        return self.__url

    def get_timeout_sec(self) -> int:
        """Return the timeout in seconds used to query the beacon."""
        return self.__timeout_sec

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
            f"{self.__url}/eth/v1/beacon/genesis", timeout=self.__timeout_sec
        )
        response.raise_for_status()
        genesis_dict = response.json()
        return Genesis(**genesis_dict)

    def get_spec(self) -> Spec:
        """Get spec data."""
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/config/spec", timeout=self.__timeout_sec
        )
        response.raise_for_status()
        spec_dict = response.json()
        return Spec(**spec_dict)

    def get_header(self, block_identifier: Union[BlockIdentierType, int]) -> Header:
        """Get a header.

        Parameters
        block_identifier: Block identifier or slot corresponding to the block to
                          retrieve
        """
        try:
            response = self.__get(
                f"{self.__url}/eth/v1/beacon/headers/{block_identifier}", timeout=self.__timeout_sec
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
                f"{self.__url}/eth/v2/beacon/blocks/{slot}", timeout=self.__timeout_sec
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

    def get_proposer_duties(self, epoch: int) -> ProposerDuties:
        """Get proposer duties

        epoch: Epoch corresponding to the proposer duties to retrieve
        """
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/validator/duties/proposer/{epoch}", timeout=self.__timeout_sec
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
            f"{self.__url}/eth/v1/beacon/states/head/validators", timeout=self.__timeout_sec
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

    def get_validators(self, slot: int) -> Validators:
        response = self.__get_retry_not_found(
            f"{self.__url}/eth/v1/beacon/states/{slot}/validators", timeout=self.__timeout_sec
        )

        # Unsure if explicit del help with memory here, let's keep it
        # for now and benchmark this in real conditions.
        response.raise_for_status()
        validators_dict = response.json()
        del response
        validators = Validators(**validators_dict)
        del validators_dict

        return validators

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
            timeout=self.__timeout_sec,
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

    def get_rewards(self, epoch: int) -> Rewards:
        """Get rewards.

        Parameters:
        epoch: Epoch corresponding to the rewards to retrieve.
        """
        response = self.__post_retry_not_found(
            f"{self.__url}/eth/v1/beacon/rewards/attestations/{epoch}",
            json=([]),
            timeout=self.__timeout_sec,
        )

        response.raise_for_status()
        rewards_dict = response.json()
        del response
        rewards = Rewards(**rewards_dict)
        del rewards_dict
        return rewards

    def get_validators_liveness(self, epoch: int, indexes: list[int]) -> ValidatorsLivenessResponse:
        """Get validators liveness.

        Parameters:
        epoch: Epoch corresponding to the validators liveness to retrieve
        """
        response = self.__post_retry_not_found(
            f"{self.__url}/eth/v1/validator/liveness/{epoch}",
            json=[f"{i}" for i in indexes],
            timeout=self.__timeout_sec,
        )

        response.raise_for_status()
        validators_liveness_dict = response.json()
        del response
        validators_liveness = ValidatorsLivenessResponse(**validators_liveness_dict)
        del validators_liveness_dict
        return validators_liveness

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
        return 
