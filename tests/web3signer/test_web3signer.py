import requests_mock

from eth_validator_watcher.web3signer import Web3Signer


def test_web3signer():
    web3signer_url = "http://web3signer:9000"
    pubkeys = ["0xaaa", "0xbbb", "0xccc"]
    expected = {"0xaaa", "0xbbb", "0xccc"}

    with requests_mock.Mocker() as mock:
        mock.get(f"{web3signer_url}/api/v1/eth2/publicKeys", json=pubkeys)
        web3signer = Web3Signer(web3signer_url)
        assert web3signer.load_pubkeys() == expected
