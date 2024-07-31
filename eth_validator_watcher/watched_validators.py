"""Watched validators.
"""

from typing import Optional

from eth_validator_watcher_ext import Validator
from .config import Config, WatchedKeyConfig
from .models import Validators, ValidatorsLivenessResponse, Rewards
from .utils import LABEL_SCOPE_ALL_NETWORK, LABEL_SCOPE_WATCHED, LABEL_SCOPE_NETWORK


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

    This is a wrapper around the C++ validator object which holds the
    state of a validator.
    """

    def __init__(self):
        # State is wrapped in a C++ object so we can perform efficient
        # operations without holding the GIL.
        #
        # We need to be careful when dealing with _v as modifications
        # can only be performed using explicit copies (i.e: do not
        # call append() on a list but rather create a new list with
        # the new element).
        self._v = Validator()

        # This gets overriden by process_config if the validator is watched.
        self._v.labels : Optional[list[str]] = [LABEL_SCOPE_ALL_NETWORK, LABEL_SCOPE_NETWORK]

    @property
    def effective_balance(self) -> int:
        """Get the effective balance of the validator.
        """
        return self._v.consensus_effective_balance

    @property
    def labels(self) -> list[str]:
        """Get the labels for the validator.
        """
        return self._v.labels

    def process_config(self, config: WatchedKeyConfig):
        """Processes a new configuration.

        Parameters:
            config: New configuration
        """
        # Even if there is no label in the config, we consider the
        # validator as watched.  This method is only called for
        # validators that are watched.
        labels = [LABEL_SCOPE_ALL_NETWORK, LABEL_SCOPE_WATCHED]
        if config.labels:
            labels = labels + config.labels

        self._v.labels = labels

    def process_epoch(self, validator: Validators.DataItem):
        """Processes a new epoch.

        Parameters:
            validator: Validator beacon state
        """
        self._v.consensus_pubkey = validator.validator.pubkey
        self._v.consensus_effective_balance = validator.validator.effective_balance
        self._v.consensus_slashed = validator.validator.slashed
        self._v.consensus_index = validator.index
        self._v.consensus_status = validator.status

    def process_liveness(self, liveness: ValidatorsLivenessResponse.Data):
        """Processes liveness data.

        Parameters:
        liveness: Validator liveness data
        """
        self._v.previous_missed_attestation = self._v.missed_attestation
        self._v.missed_attestation = liveness.is_live != True

    def process_rewards(self, ideal: Rewards.Data.IdealReward, reward: Rewards.Data.TotalReward):
        """Processes rewards data.

        Parameters:
            ideal: Ideal rewards
            reward: Actual rewards
        """
        self._v.suboptimal_source = reward.source != ideal.source
        self._v.suboptimal_target = reward.target != ideal.target
        self._v.suboptimal_head = reward.head != ideal.head

        self._v.ideal_consensus_reward = ideal.source + ideal.target + ideal.head
        self._v.actual_consensus_reward = reward.source + reward.target + reward.head

    def process_block(self, slot: int, has_block: bool):
        """Processes a block proposal.

        Parameters:
            slot: Slot of the block proposal
            missed: Whether the block was missed
        """
        if has_block:
            self._v.proposed_blocks = self._v.proposed_blocks + [slot]
        else:
            self._v.missed_blocks = self._v.missed_blocks + [slot]

    def process_block_finalized(self, slot: int, has_block: bool):
        """Processes a finalized block proposal.

        Parameters:
            slot: Slot of the block proposal
            missed: Whether the block was missed
        """
        if has_block:
            self._v.proposed_blocks_finalized = self._v.proposed_blocks_finalized + [slot]
        else:
            self._v.missed_blocks_finalized = self._v.missed_blocks_finalized + [slot]

    def process_future_block(self, slot: int):
        """Processes a future block proposal.

        Parameters:
            slot: Slot of the block proposal
        """
        self._v.future_blocks_proposal = self._v.future_blocks_proposal + [slot]

    def reset_blocks(self):
        """Reset the counters for the next run.
        """
        self._v.missed_blocks = []
        self._v.missed_blocks_finalized = []
        self._v.proposed_blocks = []
        self._v.proposed_blocks_finalized = []
        self._v.future_blocks_proposal = []


class WatchedValidators:
    """Wrapper around watched validators.

    Provides facilities to retrieve a validator by index or public
    key. This needs to be efficient both in terms of CPU and memory as
    there are about ~1 million validators on the network.
    """

    def __init__(self):
        self._validators: dict[int, WatchedValidator] = {}
        self._pubkey_to_index: dict[str, int] = {}

        self.config_initialized = False

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
        index = self._pubkey_to_index.get(normalized_public_key(pubkey))
        if index is None:
            return None
        return self._validators.get(index)

    def get_indexes(self) -> list[int]:
        """Get all validator indexes."""
        return list(self._validators.keys())

    def get_validators(self) -> dict[int, WatchedValidator]:
        """Iterate over all validators."""
        return self._validators

    def process_config(self, config: Config):
        """Process a config update.

        Parameters:
            config: Updated configuration
        """
        for item in config.watched_keys:
            index = self._pubkey_to_index.get(normalized_public_key(item.public_key), None)
            if index:
                validator = self._validators.get(index)
                if validator:
                    validator.process_config(item)

        self.config_initialized = True

    def process_epoch(self, validators: Validators):
        """Process a new epoch

        Parameters:
            validators: New validator state for the epoch from the beaconchain.
            liveness: Whether or not the validator attested in the previous epoch.
        """
        for item in validators.data:
            validator = self._validators.get(item.index)
            if validator is None:
                validator = WatchedValidator()
                self._validators[item.index] = validator
                self._pubkey_to_index[normalized_public_key(item.validator.pubkey)] = item.index

            validator.process_epoch(item)

    def process_liveness(self, liveness: ValidatorsLivenessResponse):
        """Process liveness data

        Parameters:
            liveness: Liveness data from the beacon chain
        """
        for item in liveness.data:
            validator = self._validators.get(item.index)
            if validator:
                validator.process_liveness(item)
