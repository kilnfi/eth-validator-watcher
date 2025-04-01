import os
from pathlib import Path
from eth_validator_watcher.config import load_config
from tests import assets


def test_null_config() -> None:
    path = str(Path(assets.__file__).parent / "config.null.yaml")
    config = load_config(path)

    assert config.beacon_url == 'http://localhost:5051/'
    assert config.metrics_port == 8000
    assert config.beacon_timeout_sec == 90
    assert config.network == 'mainnet'

    assert config.watched_keys == []


def test_empty_config() -> None:
    path = str(Path(assets.__file__).parent / "config.empty.yaml")
    config = load_config(path)

    assert config.beacon_url == 'http://localhost:5051/'
    assert config.beacon_timeout_sec == 90
    assert config.metrics_port == 8000
    assert config.network == 'mainnet'
    assert config.replay_start_at_ts is None
    assert config.replay_end_at_ts is None

    assert config.watched_keys == []


def test_filled_config() -> None:
    path = str(Path(assets.__file__).parent / "config.yaml")
    config = load_config(path)

    assert config.beacon_url == 'http://localhost:5051/'
    assert config.beacon_timeout_sec == 90
    assert config.metrics_port == 4242
    assert config.network == 'holesky'
    assert config.replay_start_at_ts is None
    assert config.replay_end_at_ts is None

    assert [k.public_key for k in config.watched_keys] == ['0x832b8286f5d6535fd941c6c4ed8b9b20d214fc6aa726ce4fba1c9dbb4f278132646304f550e557231b6932aa02cf08d3']


def test_filled_config_overriden() -> None:
    environ = os.environ.copy()

    os.environ['eth_watcher_beacon_url'] = 'http://override-beacon/'
    os.environ['eth_watcher_beacon_timeout_sec'] = '42'
    os.environ['eth_watcher_network'] = 'sepolia'

    path = str(Path(assets.__file__).parent / "config.yaml")
    config = load_config(path)

    assert config.beacon_url == 'http://override-beacon/'
    assert config.beacon_timeout_sec == 42
    assert config.network == 'sepolia'

    assert [k.public_key for k in config.watched_keys] == ['0x832b8286f5d6535fd941c6c4ed8b9b20d214fc6aa726ce4fba1c9dbb4f278132646304f550e557231b6932aa02cf08d3']

    os.environ.clear()
    os.environ.update(environ)
