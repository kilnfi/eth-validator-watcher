from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

import logging
import json
import yaml


class WatchedKeyConfig(BaseModel):
    """Configuration model for a watched validator key.

    Args:
        None

    Returns:
        None
    """
    public_key: str
    labels: Optional[list[str]] = None


class Config(BaseSettings):
    """Configuration model for the Ethereum Validator Watcher.

    Args:
        None

    Returns:
        None
    """
    model_config = SettingsConfigDict(case_sensitive=True, env_prefix='eth_watcher_')

    network: Optional[str] = None
    beacon_url: Optional[str] = None
    beacon_timeout_sec: Optional[int] = None
    metrics_port: Optional[int] = None
    watched_keys: Optional[List[WatchedKeyConfig]] = None

    slack_token: Optional[str] = None
    slack_channel: Optional[str] = None

    replay_start_at_ts: Optional[int] = None
    replay_end_at_ts: Optional[int] = None


def _default_config() -> Config:
    """Create and return the default configuration.

    Args:
        None

    Returns:
        Config
            The default configuration instance.
    """
    return Config(
        network='mainnet',
        beacon_url='http://localhost:5051/',
        beacon_timeout_sec=90,
        metrics_port=8000,
        watched_keys=[],
    )


def load_config(config_file: str) -> Config:
    """Load and merge configuration from environment variables and config file.

    Environment variables have priority and can be used to set secrets
    and override the config file values.

    Args:
        config_file: str
            Path to the YAML or JSON configuration file.

    Returns:
        Config
            The effective configuration used by the watcher.
    """
    with open(config_file, 'r') as fh:
        logging.info(f'⚙️ Parsing configuration file {config_file}')

        # We support json for large configuration files (500 MiB)
        # which can take time to parse with PyYAML.
        if config_file.endswith('.json'):
            config = json.load(fh)
        else:
            config = yaml.load(fh, Loader=yaml.CLoader) or dict()

        logging.info('⚙️ Validating configuration file')
        from_default = _default_config().model_dump()
        from_env = Config().model_dump()
        from_file = Config(**config).model_dump()

        logging.info('⚙️ Merging with environment variables')
        merged = from_default.copy()

        merged.update({k: v for k, v in from_file.items() if v})
        merged.update({k: v for k, v in from_env.items() if v})

        r = Config(**merged)

        logging.info('⚙️ Configuration file is ready')

        return r
