"""Contains the Beacon class which is used to interact with the consensus layer node."""

import functools
from typing import Any, Union

from requests import HTTPError, Response, Session, codes
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import ChunkedEncodingError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from .models import (
    Attestations,
    BlockIdentierType,
    Committees,
    Genesis,
    Header,
    PendingConsolidations,
    PendingDeposits,
    PendingWithdrawals,
    ProposerDuties,
    Rewards,
    Spec,
    Validators,
    ValidatorsLivenessResponse,
)


print = functools.partial(print, flush=True)


class NoBlockError(Exception):
    pass


class Beacon:
    """Beacon node abstraction."""

    def __init__(self, url: str, timeout_sec: int) -> None:
        """Initialize a Beacon instance.

        Args:
            url: str
                URL where the beacon can be reached.
            timeout_sec: int
                Timeout in seconds used to query the beacon.

        Returns:
            None
        """
        self._url = url
        self._timeout_sec = timeout_sec
        self._http_retry_not_found = Session()
        self._http = Session()
        self._first_liveness_call = True
        self._first_rewards_call = True

        adapter_retry_not_found = HTTPAdapter(
            max_retries=Retry(
                backoff_factor=1,
                total=5,
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

        self._http_retry_not_found.mount("http://", adapter_retry_not_found)
        self._http_retry_not_found.mount("https://", adapter_retry_not_found)

        self._http.mount("http://", adapter)
        self._http.mount("https://", adapter)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(ChunkedEncodingError),
    )
    def _get_retry_not_found(self, *args: Any, **kwargs: Any) -> Response:
        """Wrapper around requests.get() with retry on 404.

        Args:
            *args: Any
                Positional arguments to pass to requests.get().
            **kwargs: Any
                Keyword arguments to pass to requests.get().

        Returns:
            Response
                The HTTP response.
        """
        return self._http_retry_not_found.get(*args, **kwargs)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(ChunkedEncodingError),
    )
    def _get(self, *args: Any, **kwargs: Any) -> Response:
        """Wrapper around requests.get().

        Args:
            *args: Any
                Positional arguments to pass to requests.get().
            **kwargs: Any
                Keyword arguments to pass to requests.get().

        Returns:
            Response
                The HTTP response.
        """
        return self._http.get(*args, **kwargs)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(ChunkedEncodingError),
    )
    def _post_retry_not_found(self, *args: Any, **kwargs: Any) -> Response:
        """Wrapper around requests.post() with retry on 404.

        Args:
            *args: Any
                Positional arguments to pass to requests.post().
            **kwargs: Any
                Keyword arguments to pass to requests.post().

        Returns:
            Response
                The HTTP response.
        """
        return self._http_retry_not_found.post(*args, **kwargs)

    def get_url(self) -> str:
        """Get the URL of the beacon node.

        Args:
            None

        Returns:
            str
                The URL of the beacon node.
        """
        return self._url

    def get_timeout_sec(self) -> int:
        """Get the timeout in seconds used to query the beacon.

        Args:
            None

        Returns:
            int
                The timeout in seconds.
        """
        return self._timeout_sec

    def get_genesis(self) -> Genesis:
        """Get beacon chain genesis data.

        Args:
            None

        Returns:
            Genesis
                The beacon chain genesis data.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/beacon/genesis", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return Genesis.model_validate_json(response.text)

    def get_spec(self) -> Spec:
        """Get beacon chain specification data.

        Args:
            None

        Returns:
            Spec
                The beacon chain specification data.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/config/spec", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return Spec.model_validate_json(response.text)

    def get_committees(self, slot: int) -> Committees:
        """Get beacon chain committees for a specific slot.

        Args:
            slot: int
                Slot corresponding to the committees to retrieve.

        Returns:
            Committees
                The committee assignments for the specified slot.
        """
        response = self._get(
            f"{self._url}/eth/v1/beacon/states/{slot}/committees?slot={slot}", timeout=self._timeout_sec
        )
        response.raise_for_status()

        return Committees.model_validate_json(response.text)

    def get_attestations(self, slot: int) -> Attestations:
        """Get attestations from a specific block.

        Args:
            slot: int
                Slot corresponding to the block in which attestations are present.

        Returns:
            Attestations
                The attestations from the specified block, or None if the block doesn't exist.
        """
        try:
            response = self._get(
                f"{self._url}/eth/v2/beacon/blocks/{slot}/attestations", timeout=self._timeout_sec
            )
            response.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == codes.not_found:
                return None
            # If we are here, it's an other error
            raise

        return Attestations.model_validate_json(response.text)

    def get_header(self, block_identifier: Union[BlockIdentierType, int]) -> Header:
        """Get a block header.

        Args:
            block_identifier: Union[BlockIdentierType, int]
                Block identifier or slot corresponding to the block to retrieve.

        Returns:
            Header
                The block header for the specified block.

        Raises:
            NoBlockError: If the block does not exist.
            HTTPError: For other HTTP errors.
        """
        try:
            response = self._get(
                f"{self._url}/eth/v1/beacon/headers/{block_identifier}", timeout=self._timeout_sec
            )
            response.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == codes.not_found:
                # If we are here, it means the block does not exist
                raise NoBlockError from e
            # If we are here, it's an other error
            raise

        return Header.model_validate_json(response.text)

    def get_proposer_duties(self, epoch: int) -> ProposerDuties:
        """Get proposer duties for a specific epoch.

        Args:
            epoch: int
                Epoch corresponding to the proposer duties to retrieve.

        Returns:
            ProposerDuties
                The proposer duties for the specified epoch.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/validator/duties/proposer/{epoch}", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return ProposerDuties.model_validate_json(response.text)

    def get_validators(self, slot: int) -> Validators:
        """Get validator information for a specific slot.

        Args:
            slot: int
                Slot for which to retrieve validator information.

        Returns:
            Validators
                The validator information for the specified slot.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/beacon/states/{slot}/validators", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return Validators.model_validate_json(response.text)

    def get_rewards(self, epoch: int) -> Rewards:
        """Get attestation rewards for a specific epoch.

        Args:
            epoch: int
                Epoch corresponding to the rewards to retrieve.

        Returns:
            Rewards
                The attestation rewards for the specified epoch.
        """
        response = self._post_retry_not_found(
            f"{self._url}/eth/v1/beacon/rewards/attestations/{epoch}",
            json=([]),
            timeout=self._timeout_sec,
        )

        response.raise_for_status()

        return Rewards.model_validate_json(response.text)

    def get_validators_liveness(self, epoch: int, indexes: list[int]) -> ValidatorsLivenessResponse:
        """Get validators liveness information for a specific epoch.

        Args:
            epoch: int
                Epoch corresponding to the validators liveness to retrieve.
            indexes: list[int]
                List of validator indexes to check liveness for.

        Returns:
            ValidatorsLivenessResponse
                The liveness information for the specified validators.
        """
        response = self._post_retry_not_found(
            f"{self._url}/eth/v1/validator/liveness/{epoch}",
            json=[f"{i}" for i in indexes],
            timeout=self._timeout_sec,
        )

        response.raise_for_status()

        return ValidatorsLivenessResponse.model_validate_json(response.text)

    def get_pending_deposits(self) -> PendingDeposits:
        """Get beacon chain pending deposits.

        Args:
            None

        Returns:
            PendingDeposits
                The beacon chain pending deposits.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/beacon/states/head/pending_deposits", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return PendingDeposits.model_validate_json(response.text)

    def get_pending_consolidations(self) -> PendingConsolidations:
        """Get beacon chain pending consolidations.

        Args:
            None

        Returns:
            PendingConsolidations
                The beacon chain pending consolidations.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/beacon/states/head/pending_consolidations", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return PendingConsolidations.model_validate_json(response.text)

    def get_pending_withdrawals(self) -> PendingWithdrawals:
        """Get beacon chain pending withdrawals.

        Args:
            None

        Returns:
            PendingWithdrawals
                The beacon chain pending withdrawals.
        """
        response = self._get_retry_not_found(
            f"{self._url}/eth/v1/beacon/states/head/pending_partial_withdrawals", timeout=self._timeout_sec
        )

        response.raise_for_status()

        return PendingWithdrawals.model_validate_json(response.text)

    def has_block_at_slot(self, block_identifier: BlockIdentierType | int) -> bool:
        """Returns the slot of a block identifier if it exists.

        Args:
        -----
        block_identifier: BlockIdentierType | int
            Block identifier (i.e: head, finalized, 42, etc).

        Returns:
        --------
        bool: True if the block exists, False otherwise.
        """
        try:
            return self.get_header(block_identifier).data.header.message.slot > 0
        except NoBlockError:
            return False
