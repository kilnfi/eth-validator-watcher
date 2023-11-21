"""Contains the Execution class which is used to interact with the execution layer node."""


from requests import Session, codes
from requests.adapters import HTTPAdapter, Retry

from eth_validator_watcher.models import EthGetBlockByHashRequest, ExecutionBlock


class Execution:
    """Execution node abstraction."""

    def __init__(self, url: str) -> None:
        """Execution node

        url: URL where the execution node can be reached
        """
        self.__url = url
        self.__http = Session()

        adapter = HTTPAdapter(
            max_retries=Retry(
                backoff_factor=0.5,
                total=3,
                status_forcelist=[codes.not_found],
            )
        )

        self.__http.mount("http://", adapter)
        self.__http.mount("https://", adapter)

    def eth_get_block_by_hash(self, hash: str) -> ExecutionBlock:
        """Get execution block.

        Parameters:
        hash: Hash of the block to retrieve
        """
        request_body = EthGetBlockByHashRequest(params=[hash, True])
        response = self.__http.post(self.__url, json=request_body.model_dump())
        response.raise_for_status()
        execution_block_dict = response.json()
        return ExecutionBlock(**execution_block_dict)
