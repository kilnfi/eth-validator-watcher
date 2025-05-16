"""Classes and functions for managing watched validators."""

from typing import Optional

from eth_validator_watcher_ext import Validator
from .config import Config, WatchedKeyConfig
from .models import Validators, ValidatorsLivenessResponse, Rewards
from .utils import LABEL_SCOPE_ALL_NETWORK, LABEL_SCOPE_WATCHED, LABEL_SCOPE_NETWORK


def normalized_public_key(pubkey: str) -> str:
    """Normalize a validator public key by removing 0x prefix and lowercasing.

    Args:
        pubkey: str
            Public key to normalize.

    Returns:
        str
            Normalized public key.
    """
    if pubkey.startswith('0x'):
        pubkey = pubkey[2:]
    return pubkey.lower()


class WatchedValidator:
    """Watched validator abstraction.

    This is a wrapper around the C++ validator object which holds the
    state of a validator.

    Args:
        None

    Returns:
        None
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
        self._v.labels: Optional[list[str]] = [LABEL_SCOPE_ALL_NETWORK, LABEL_SCOPE_NETWORK]

    @property
    def effective_balance(self) -> int:
        """Get the effective balance of the validator.

        Args:
            None

        Returns:
            int
                The effective balance of the validator in Gwei.
        """
        return self._v.consensus_effective_balance

    @property
    def labels(self) -> list[str]:
        """Get the labels for the validator.

        Args:
            None

        Returns:
            list[str]
                List of labels associated with this validator.
        """
        return self._v.labels

    def process_config(self, config: WatchedKeyConfig):
        """Process a new configuration for this validator.

        Args:
            config: WatchedKeyConfig
                New configuration for this validator.

        Returns:
            None
        """
        # Even if there is no label in the config, we consider the
        # validator as watched.  This method is only called for
        # validators that are watched.
        labels = [LABEL_SCOPE_ALL_NETWORK, LABEL_SCOPE_WATCHED]
        if config.labels:
            labels = labels + config.labels

        self._v.labels = labels

    def process_epoch(self, validator: Validators.DataItem):
        """Process validator state for a new epoch.

        Args:
            validator: Validators.DataItem
                Validator beacon state data.

        Returns:
            None
        """
        self._v.consensus_pubkey = validator.validator.pubkey
        self._v.consensus_effective_balance = validator.validator.effective_balance
        self._v.weight = validator.validator.effective_balance / 32_000_000_000
        self._v.consensus_slashed = validator.validator.slashed
        self._v.consensus_index = validator.index
        self._v.consensus_status = validator.status
        self._v.consensus_activation_epoch = validator.validator.activation_epoch
        self._v.consensus_type = int(validator.validator.withdrawal_credentials[2:4], 16)

    def process_liveness(self, liveness: ValidatorsLivenessResponse.Data, current_epoch: int):
        """Processes liveness data.

        Args:
            liveness: ValidatorsLivenessResponse.Data
                Validator liveness data.
            current_epoch: int
                Current epoch.
        """
        # Because we ask for the liveness of the previous epoch, we
        # need to dismiss validators that weren't activated yet at
        # that time to prevent false positive.
        if (current_epoch - 1) >= self._v.consensus_activation_epoch:
            self._v.previous_missed_attestation = self._v.missed_attestation
            self._v.missed_attestation = not liveness.is_live

    def process_rewards(self, ideal: Rewards.Data.IdealReward, reward: Rewards.Data.TotalReward):
        """Process validator rewards data.

        Args:
            ideal: Rewards.Data.IdealReward
                Ideal rewards that could have been earned.
            reward: Rewards.Data.TotalReward
                Actual rewards earned by the validator.

        Returns:
            None
        """
        self._v.suboptimal_source = reward.source != ideal.source
        self._v.suboptimal_target = reward.target != ideal.target
        self._v.suboptimal_head = reward.head != ideal.head

        self._v.ideal_consensus_reward = ideal.source + ideal.target + ideal.head
        self._v.actual_consensus_reward = reward.source + reward.target + reward.head

    def process_duties(self, slot: int, performed: bool):
        """Process a validator attestation duty.

        Args:
            slot: int
                Slot for which there is or is not an attestation for the validator.
            performed: bool
                Whether or not the validator attested in this slot.

        Returns:
            None
        """
        self._v.duties_slot = slot
        self._v.duties_performed_at_slot = performed

    def process_block(self, slot: int, has_block: bool):
        """Processes a block proposal.

        Args:
            slot: int
                Slot of the block proposal.
            has_block: bool
                Whether the block was found (True) or missed (False).
        """
        if has_block:
            self._v.proposed_blocks = self._v.proposed_blocks + [slot]
        else:
            self._v.missed_blocks = self._v.missed_blocks + [slot]

    def process_block_finalized(self, slot: int, has_block: bool):
        """Processes a finalized block proposal.

        Args:
            slot: int
                Slot of the block proposal.
            has_block: bool
                Whether the block was found (True) or missed (False).
        """
        if has_block:
            self._v.proposed_blocks_finalized = self._v.proposed_blocks_finalized + [slot]
        else:
            self._v.missed_blocks_finalized = self._v.missed_blocks_finalized + [slot]

    def process_future_block(self, slot: int):
        """Process a future block proposal assignment.

        Args:
            slot: int
                Slot of the future block proposal.

        Returns:
            None
        """
        self._v.future_blocks_proposal = self._v.future_blocks_proposal + [slot]

    def reset_blocks(self):
        """Reset the block counters for the next run.

        Args:
            None

        Returns:
            None
        """
        self._v.missed_blocks = []
        self._v.missed_blocks_finalized = []
        self._v.proposed_blocks = []
        self._v.proposed_blocks_finalized = []
        self._v.future_blocks_proposal = []


class WatchedValidators:
    """Registry and manager for watched validators.

    Provides facilities to retrieve a validator by index or public
    key. This needs to be efficient both in terms of CPU and memory as
    there are about ~1 million validators on the network.

    Args:
        None

    Returns:
        None
    """

    def __init__(self):
        self._validators: dict[int, WatchedValidator] = {}
        self._pubkey_to_index: dict[str, int] = {}

        self.config_initialized = False

    def get_validator_by_index(self, index: int) -> Optional[WatchedValidator]:
        """Get a validator by index.

        Args:
            index: int
                Index of the validator to retrieve.

        Returns:
            Optional[WatchedValidator]: The validator with the given index, or None if not found.
        """
        return self._validators.get(index)

    def get_validator_by_pubkey(self, pubkey: str) -> Optional[WatchedValidator]:
        """Get a validator by public key.

        Args:
            pubkey: str
                Public key of the validator to retrieve.

        Returns:
            Optional[WatchedValidator]: The validator with the given public key, or None if not found.
        """
        index = self._pubkey_to_index.get(normalized_public_key(pubkey))
        if index is None:
            return None
        return self._validators.get(index)

    def get_indexes(self) -> list[int]:
        """Get all validator indexes.

        Returns:
            list[int]: A list of all validator indices in the registry.
        """
        return list(self._validators.keys())

    def get_validators(self) -> dict[int, WatchedValidator]:
        """Get all validators in the registry.

        Returns:
            dict[int, WatchedValidator]: A dictionary mapping validator indices to WatchedValidator objects.
        """
        return self._validators

    def process_config(self, config: Config):
        """Process a configuration update for watched validators.

        Args:
            config: Config
                Updated configuration containing watched keys.

        Returns:
            None
        """
        for item in config.watched_keys:
            index = self._pubkey_to_index.get(normalized_public_key(item.public_key), None)
            if index:
                validator = self._validators.get(index)
                if validator:
                    validator.process_config(item)

        self.config_initialized = True

    def process_epoch(self, validators: Validators):
        """Process validator state data for a new epoch.

        Args:
            validators: Validators
                New validator state for the epoch from the beacon chain.

        Returns:
            None
        """
        for item in validators.data:
            validator = self._validators.get(item.index)
            if validator is None:
                validator = WatchedValidator()
                self._validators[item.index] = validator
                self._pubkey_to_index[normalized_public_key(item.validator.pubkey)] = item.index

            validator.process_epoch(item)

    def process_liveness(self, liveness: ValidatorsLivenessResponse, current_epoch: int):
        """Process validator liveness data.

        Args:
            liveness: ValidatorsLivenessResponse
                Liveness data from the beacon chain.
            current_epoch: int
                Current epoch being processed.

        Returns:
            None
        """
        for item in liveness.data:
            validator = self._validators.get(item.index)
            if validator:
                validator.process_liveness(item, current_epoch)
