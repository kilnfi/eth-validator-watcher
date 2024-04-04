"""Watched validators.

This module provides a wrapper around per-validator computations
before exposing them later to prometheus. There are 4 types of
processing performed:

- process_config: configuration update (per-key labels)
- process_epoch: new epoch processing (beacon chain status update)
- process_missed_attestations: missed attestation processing (slot 16)
- process_rewards: rewards processing (slot 17)

WatchedValidator which holds the state of a validator while
WatchedValidators handles the collection of all validators, providing
efficient ways to access them which are then used by the prometheus
exporter.
"""

import logging

from typing import Optional

from .config import Config, WatchedKeyConfig
from .models import Validators
from .utils import LABEL_SCOPE_NETWORK, LABEL_SCOPE_WATCHED


def normalized_public_key(pubkey: str) -> str:
    """Normalize a public key.

    Parameters:
        pubkey: Public key to normalize
    """
    if pubkey.startswith('0x'):
        pubkey = pubkey[2:]
    return pubkey.lower()


class WatchedValidator:
    """Watched validator abstraction.

    This needs to be optimized for both CPU and memory usage as it
    will be instantiated for every validator of the network.

    Attributes:
        index: Validator index
        pubkey: Validator public key
        status: Validator status for the current epoch
        previous_status: Validator previous status for the previous epoch
        labels: Validator labels
        missed_attestation: Validator missed attestation for the current epoch
        previous_missed_attestation: Validator missed previous attestation for the previous epoch
        suboptimal_source: Validator suboptimal source for the current epoch
        suboptimal_target: Validator suboptimal target for the current epoch
        suboptimal_head: Validator suboptimal head for the current epoch
        beacon_validator: Latest state of the validator from the beacon chain
    """

    def __init__(self):
        self.index : int = 0
        self.previous_status : Validators.DataItem.StatusEnum | None = None
        self._labels : Optional[list[str]] = None
        self.missed_attestation : bool | None = None
        self.previous_missed_attestation : bool | None = None
        self.suboptimal_source : bool | None = None
        self.suboptimal_target : bool | None = None
        self.suboptimal_head : bool | None = None
        self.beacon_validator : Validators.DataItem | None = None

    @property
    def pubkey(self) -> str:
        """Get the public key of the validator.
        """
        return normalized_public_key(self.beacon_validator.validator.pubkey)

    @property
    def status(self) -> Validators.DataItem.StatusEnum:
        """Get the status of the validator.
        """
        return self.beacon_validator.status

    @property
    def labels(self) -> list[str]:
        """Get the labels for the validator.
        """
        configured = self._labels or []
        return configured + [LABEL_SCOPE_NETWORK, LABEL_SCOPE_WATCHED]

    def process_config(self, config: WatchedKeyConfig):
        """Processes a new configuration.

        Parameters:
            config: New configuration
        """
        self._labels = config.labels

    def process_epoch(self, validator: Validators.DataItem):
        """Processes a new epoch.

        Parameters:
            validator: Validator beacon state
        """
        if self.beacon_validator is not None:
            self.previous_status = self.status

        self.previous_missed_attestation = self.missed_attestation
        self.missed_attestation = None

        self.suboptimal_source = None
        self.suboptimal_target = None
        self.suboptimal_head = None

        self.beacon_validator = validator


class WatchedValidators:
    """Wrapper around watched validators.

    Provides facilities to retrieve a validator by index or public
    key. This needs to be efficient both in terms of CPU and memory as
    there are about ~1 million validators on the network.
    """

    def __init__(self):
        self._validators: dict[int, WatchedValidator] = {}
        self._pubkey_to_index: dict[str, int] = {}

    def get_validator_by_index(self, index: int) -> Optional[WatchedValidator]:
        """Get a validator by index.

        Parameters:
            index: Index of the validator to retrieve
        """
        return self._validators.get(index)

    def get_validator_by_pubkey(self, pubkey: str) -> Optional[WatchedValidator]:
        """Get a validator by public key.

        Parameters:
            pubkey: Public key of the validator to retrieve
        """
        index = self._pubkey_to_index.get(pubkey)
        if index is None:
            return None
        return self._validators.get(index)

    def get_validators(self) -> dict[int, WatchedValidator]:
        """Get all validators."""
        return self._validators

    def process_config(self, config: Config):
        """Process a config update

        Parameters:
            config: Updated configuration
        """
        logging.info('Processing config & validator labels')

        unknown = 0
        for item in config.watched_keys:
            updated = False
            index = self._pubkey_to_index.get(normalized_public_key(item.public_key), None)
            if index:
                validator = self._validators.get(index)
                if validator:
                    validator.process_config(item)
                    updated = True
            if not updated:
                unknown += 1

        logging.info(f'Config processed ({unknown} unknown validators were skipped)')

    def process_epoch(self, validators: Validators):
        """Process a new epoch

        Parameters:
            validators: New validator state for the epoch from the beaconchain.
        """
        logging.info('Processing new epoch')

        for item in validators.data:
            validator = self._validators.get(item.index)
            if validator is None:
                validator = WatchedValidator()
                self._validators[item.index] = validator
                self._pubkey_to_index[normalized_public_key(item.validator.pubkey)] = item.index

            validator.process_epoch(item)

        logging.info(f'New epoch processed ({len(validators.data)} validators)')
