from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, List, Optional

import logging
import json
import os
import yaml


class WatchedKeyConfig(BaseModel):
    """Configuration of a watched key.
    """
    public_key: str
    labels: Optional[list[str]] = None


class Config(BaseSettings):
    """Configuration of the Ethereum Validator Watcher.
    """
    model_config = SettingsConfigDict(case_sensitive=True, env_prefix='eth_watcher_')

    network: Optional[str] = None
    beacon_url: Optional[str] = None
    beacon_timeout_sec: Optional[int] = 90
    metrics_port: Optional[int] = 8000
    start_at: Optional[int] = None
    watched_keys: Optional[List[WatchedKeyConfig]] = None


def load_config(config_file: str) -> Config:
    """Loads the configuration file from environment and configfile.

    Environment variables have priority (can be used to set secrets
    and override the config file).
    
    Parameters:
    config_file : path to the YAML configuration file

    Returns:
    The effective configuration used by the watcher
    """
    with open(config_file, 'r') as fh:
        logging.info(f'parsing configuration file {config_file}')

        # We support json for large configuration files (500 MiB)
        # which can take time to parse with PyYAML.
        if config_file.endswith('.json'):
            config = json.load(fh)
        else:
            config = yaml.load(fh, Loader=yaml.CLoader) or dict()

        logging.info(f'validating configuration file')
        from_env = Config().model_dump()
        from_file = Config(**config).model_dump()

        logging.info(f'merging with environment variables')
        merged = from_file.copy()
        merged.update({k: v for k, v in from_env.items() if v})
        r = Config(**merged)

        logging.info(f'configuration file is ready')

        return r
