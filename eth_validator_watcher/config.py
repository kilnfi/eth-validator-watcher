from dataclasses import dataclass, field
from typing import Any, List, Optional

import os
import yaml


@dataclass
class WatchedKeyConfig:
    """Configuration of a watched key.
    """
    public_key: str
    labels: Optional[list[str]] = None
    fee_recipient: Optional[str] = None


@dataclass
class Config:
    """Configuration of the Ethereum Validator Watcher.

    Everything can be configured via a configuration file, there is
    the possibility to override parts of the configuration with
    environment variables, which ca be useful for secrets.

    Settings here are split in two groups: the ones that can be overriden,
    and the more complex ones that can't.
    """
    beacon_url: Optional[str] = os.getenv('ETH_WATCHER_BEACON_URL')
    beacon_type: Optional[str] = os.getenv('ETH_WATCHER_BEACON_TYPE')
    execution_url: Optional[str] = os.getenv('ETH_WATCHER_EXEC_URL')
    config_file: Optional[str] = os.getenv('ETH_WATCHER_CONFIG_FILE', 'etc/config.local.yaml')
    web3signer_url: Optional[str] = os.getenv('ETH_WATCHER_WEB3SIGNER_URL')
    default_fee_recipient: Optional[str] = os.getenv('ETH_WATCHER_DEFAULT_FEE_RECIPIENT')
    slack_channel: Optional[str] = os.getenv('ETH_WATCHER_SLACK_CHANNEL')
    slack_token: Optional[str] = os.getenv('ETH_WATCHER_SLACK_TOKEN')
    relay_url: Optional[List[str]] = field(default_factory=lambda: os.getenv('ETH_WATCHER_RELAY_URL', '').split(','))
    liveness_file: Optional[str] = os.getenv('ETH_WATCHER_LIVENESS_FILE')

    watched_keys: Optional[List[WatchedKeyConfig]] = None


def load_config(config_file: str) -> Config:
    """Loads the configuration file

    Parameters:
    config_file : path to the YAML configuration file
    """
    with open(config_file, 'r') as fh:
        yml = yaml.safe_load(fh)
        config = Config()

        def get_value(value: Any, key: str) -> Any:
            if value is not None:
                return value
            return yml.get(key)

        # Settings that can be overriden via environment.
        config.beacon_url = get_value(config.beacon_url, 'beacon_url')
        config.execution_url = get_value(config.execution_url, 'execution_url')
        config.web3signer_url = get_value(config.web3signer_url, 'web3signer_url')
        config.default_fee_recipient = get_value(config.default_fee_recipient, 'default_fee_recipient')
        config.slack_channel = get_value(config.slack_channel, 'slack_channel')
        config.slack_token = get_value(config.slack_token, 'slack_token')
        config.beacon_type = get_value(config.beacon_type, 'beacon_type')
        config.relay_url = get_value(config.relay_url, 'relay_url')
        config.liveness_file = get_value(config.liveness_file, 'liveness_file')

        # More complex settings that can't.
        config.watched_keys = [
            WatchedKeyConfig(
                public_key=config_key.get('public_key'),
                labels=config_key.get('label'),
                fee_recipient=config_key.get('fee_recipient', config.default_fee_recipient),
            ) for config_key in yml.get('watched_keys')
        ]

        return config
