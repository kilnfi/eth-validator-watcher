import requests


class Web3Signer:
    def __init__(self, url: str) -> None:
        """Web3Signer

        url: URL where Web3Signer can be reached
        """
        self.__url = url

    def load_pubkeys(self) -> set[str]:
        """Load public keys from Web3Signer.

        Returns the corresponding set of public keys.
        """
        resp = requests.get(f"{self.__url}/api/v1/eth2/publicKeys")
        return set(resp.json())
