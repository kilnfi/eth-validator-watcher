from .models import BeaconType
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, List, Optional

import os
import yaml


class WatchedKeyConfig(BaseModel):
    """Configuration of a watched key.
    """
    public_key: str
    labels: Optional[list[str]] = None
    fee_recipient: Optional[str] = None


class Config(BaseSettings):
    """Configuration of the Ethereum Validator Watcher.
    """
    model_config = SettingsConfigDict(case_sensitive=True, env_prefix='eth_watcher_')

    beacon_url: Optional[str] = None
    beacon_type: BeaconType = BeaconType.OTHER
    beacon_timeout_sec: int = 90
    execution_url: Optional[str] = None
    web3signer_url: Optional[str] = None
    default_fee_recipient: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_token: Optional[str] = None
    relays: Optional[List[str]] = None
    liveness_file: Optional[str] = None
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
        config = yaml.safe_load(fh) or dict()

        from_env = Config().model_dump()
        from_yaml = Config(**config).model_dump()

        merged = from_yaml.copy()
        merged.update({k: v for k, v in from_env.items() if v})

        return Config(**merged)
