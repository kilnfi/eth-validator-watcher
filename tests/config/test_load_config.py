from pathlib import Path

from eth_validator_watcher.config import load_config


def test_empty_config() -> None:
    Path(assets.__file__).parent / ""
    config = load_config()
