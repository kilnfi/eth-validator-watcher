from pathlib import Path
from eth_validator_watcher.config import load_config, WatchedKeyConfig
from eth_validator_watcher.models import BeaconType
from tests.config import assets


def test_empty_config() -> None:
    path = Path(assets.__file__).parent / "config.empty.yaml"
    config = load_config(path)

    assert config.beacon_url is None
    assert config.execution_url is None
    assert config.web3signer_url is None
    assert config.default_fee_recipient is None
    assert config.slack_channel is None
    assert config.slack_token is None
    assert config.beacon_type == BeaconType.OTHER
    assert config.relays is None
    assert config.liveness_file is None

    assert config.watched_keys == []


def test_filled_config() -> None:
    path = Path(assets.__file__).parent / "config.yaml"
    config = load_config(path)

    assert config.beacon_url == 'http://localhost:5051/'
    assert config.execution_url == 'http://localhost:8545/'
    assert config.web3signer_url == 'http://web3signer:9000/'
    assert config.default_fee_recipient == '0x41bF25fC8C52d292bD66D3BCEcd8a919ecB9EF88'
    assert config.slack_channel == '#ethereum-monitoring'
    assert config.slack_token == 'secret'
    assert config.beacon_type == BeaconType.OTHER
    assert config.relays == ['http://relay1', 'http://relay2']
    assert config.liveness_file == '/tmp/i-am-alive'

    assert [k.public_key for k in config.watched_keys] == ['0x832b8286f5d6535fd941c6c4ed8b9b20d214fc6aa726ce4fba1c9dbb4f278132646304f550e557231b6932aa02cf08d3']
