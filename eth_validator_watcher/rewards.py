"""Contains functions to handle rewards calculation"""

from .models import Rewards
from .watched_validators import WatchedValidators


def process_rewards(validators: WatchedValidators, rewards: Rewards) -> None:
    """Processes rewards for all validators.

    Args:
        validators: WatchedValidators
            The registry of validators being watched.
        rewards: Rewards
            The rewards data to process.

    Returns:
        None
    """
    ideal_by_eb: dict[int, Rewards.Data.IdealReward] = {}
    for ideal_reward in rewards.data.ideal_rewards:
        ideal_by_eb[ideal_reward.effective_balance] = ideal_reward

    for reward in rewards.data.total_rewards:
        validator = validators.get_validator_by_index(reward.validator_index)
        if not validator:
            continue

        ideal = ideal_by_eb.get(validator.effective_balance)
        if not ideal:
            continue

        validator.process_rewards(ideal, reward)
