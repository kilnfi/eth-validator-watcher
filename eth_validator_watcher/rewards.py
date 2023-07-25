"""Contains functions to handle rewards calculation"""

from typing import Tuple
from .beacon import Beacon
from .models import BeaconType, Validators

from prometheus_client import Gauge, Counter


Validator = Validators.DataItem.Validator

Reward = Tuple[int, int, int]  # source, target, head
AreIdeal = Tuple[bool, bool, bool]  # source, target, head

suboptimal_sources_rate_gauge = Gauge(
    "suboptimal_sources_rate", "Suboptimal sources rate"
)

suboptimal_targets_rate_gauge = Gauge(
    "suboptimal_targets_rate", "Suboptimal targets rate"
)

suboptimal_heads_rate_gauge = Gauge("suboptimal_heads_rate", "Suboptimal heads rate")

ideal_sources_count = Counter("ideal_sources_count", "Ideal sources count")
ideal_targets_count = Counter("ideal_targets_count", "Ideal targets count")
ideal_heads_count = Counter("ideal_heads_count", "Ideal heads count")

actual_positive_sources_count = Counter(
    "actual_positive_sources_count", "Actual positive sources count"
)

actual_negative_sources_count = Counter(
    "actual_negative_sources_count", "Actual negative sources count"
)

actual_positive_targets_count = Counter(
    "actual_positive_targets_count", "Actual positive targets count"
)

actual_negative_targets_count = Counter(
    "actual_negative_targets_count", "Actual negative targets count"
)

actual_heads_count = Counter("actual_heads_count", "Actual heads count")


def process_rewards(
    beacon: Beacon,
    beacon_type: BeaconType,
    epoch: int,
    index_to_validator: dict[int, Validator],
) -> None:
    """Process rewards for given epoch and validators

    Parameters:
        beacon (Beacon): Beacon object
        beacon_type (BeaconType): Beacon type
        epoch (int): Epoch number
        index_to_validator (dict[int, Validator]): Dictionary with:
            key: validator index
            value: Validator object
    """
    if len(index_to_validator) == 0:
        return

    data = beacon.get_rewards(beacon_type, epoch - 2, set(index_to_validator)).data

    if len(data.ideal_rewards) == 0 and len(data.total_rewards) == 0:
        # We probably are connected to a beacon that does not support rewards
        return

    effective_balance_to_ideal_reward: dict[int, Reward] = {
        reward.effective_balance: (reward.source, reward.target, reward.head)
        for reward in data.ideal_rewards
    }

    index_to_actual_reward: dict[int, Reward] = {
        reward.validator_index: (reward.source, reward.target, reward.head)
        for reward in data.total_rewards
    }

    items = [
        _process_validator(
            validator.pubkey,
            effective_balance_to_ideal_reward[validator.effective_balance],
            index_to_actual_reward[index],
        )
        for index, validator in index_to_validator.items()
    ]

    unzipped: Tuple[
        Tuple[str], Tuple[Reward], Tuple[Reward], Tuple[AreIdeal]
    ] = zip(  # type:ignore
        *items
    )

    pubkeys, ideal_rewards, actual_rewards, ideals = unzipped

    ideal_sources, ideal_targets, ideal_heads = zip(*ideal_rewards)
    actual_sources, actual_targets, actual_heads = zip(*actual_rewards)
    are_sources_ideal, are_targets_ideal, are_heads_ideal = zip(*ideals)

    total_ideal_sources = sum(ideal_sources)
    total_ideal_targets = sum(ideal_targets)
    total_ideal_heads = sum(ideal_heads)

    ideal_sources_count.inc(total_ideal_sources)
    ideal_targets_count.inc(total_ideal_targets)
    ideal_heads_count.inc(total_ideal_heads)

    total_actual_sources = sum(actual_sources)
    total_actual_targets = sum(actual_targets)
    total_actual_heads = sum(actual_heads)

    actual_sources_count = (
        actual_positive_sources_count
        if total_actual_sources >= 0
        else actual_negative_sources_count
    )

    actual_targets_count = (
        actual_positive_targets_count
        if total_actual_targets >= 0
        else actual_negative_targets_count
    )

    actual_sources_count.inc(abs(total_actual_sources))
    actual_targets_count.inc(abs(total_actual_targets))
    actual_heads_count.inc(abs(total_actual_heads))

    suboptimal_sources_rate = 1 - sum(are_sources_ideal) / len(are_sources_ideal)
    suboptimal_targets_rate = 1 - sum(are_targets_ideal) / len(are_targets_ideal)
    suboptimal_heads_rate = 1 - sum(are_heads_ideal) / len(are_heads_ideal)

    suboptimal_sources_rate_gauge.set(suboptimal_sources_rate)
    suboptimal_targets_rate_gauge.set(suboptimal_targets_rate)
    suboptimal_heads_rate_gauge.set(suboptimal_heads_rate)

    # Source
    not_perfect_source_pubkeys = {
        pubkey for (pubkey, perfect) in zip(pubkeys, are_sources_ideal) if not perfect
    }

    if len(not_perfect_source_pubkeys) > 0:
        first_not_perfect_source_pubkeys = sorted(not_perfect_source_pubkeys)[:5]

        short_first_not_perfect_source_pubkeys = [
            pubkey[:10] for pubkey in first_not_perfect_source_pubkeys
        ]

        short_first_not_perfect_source_pubkeys_str = ", ".join(
            short_first_not_perfect_source_pubkeys
        )

        diff = len(not_perfect_source_pubkeys) - len(first_not_perfect_source_pubkeys)

        print(
            f"🚰 Our validator {short_first_not_perfect_source_pubkeys_str} and {diff} "
            f"more had not ideal rewards on source at epoch {epoch-2} "
            f"({suboptimal_sources_rate:.2%})"
        )

    # Target
    not_perfect_target_pubkeys = {
        pubkey for (pubkey, perfect) in zip(pubkeys, are_targets_ideal) if not perfect
    }

    if len(not_perfect_target_pubkeys) > 0:
        first_not_perfect_target_pubkeys = sorted(not_perfect_target_pubkeys)[:5]

        short_first_not_perfect_target_pubkeys = [
            pubkey[:10] for pubkey in first_not_perfect_target_pubkeys
        ]

        short_first_not_perfect_target_pubkeys_str = ", ".join(
            short_first_not_perfect_target_pubkeys
        )

        diff = len(not_perfect_target_pubkeys) - len(first_not_perfect_target_pubkeys)

        print(
            f"🎯 Our validator {short_first_not_perfect_target_pubkeys_str} and {diff} "
            f"more had not ideal rewards on target at epoch {epoch-2} "
            f"({suboptimal_targets_rate:.2%})"
        )

    # Head
    not_perfect_head_pubkeys = {
        pubkey for (pubkey, perfect) in zip(pubkeys, are_heads_ideal) if not perfect
    }

    if len(not_perfect_head_pubkeys) > 0:
        first_not_perfect_head_pubkeys = sorted(not_perfect_head_pubkeys)[:5]

        short_first_not_perfect_head_pubkeys = [
            pubkey[:10] for pubkey in first_not_perfect_head_pubkeys
        ]

        short_first_not_perfect_head_pubkeys_str = ", ".join(
            short_first_not_perfect_head_pubkeys
        )

        diff = len(not_perfect_head_pubkeys) - len(first_not_perfect_head_pubkeys)

        print(
            f"🗣️ Our validator {short_first_not_perfect_head_pubkeys_str} and {diff} "
            f"more had not ideal rewards on head  at epoch {epoch-2} "
            f"({suboptimal_heads_rate:.2%})"
        )


def _process_validator(
    pubkey: str,
    ideal_reward: Reward,
    actual_reward: Reward,
) -> Tuple[str, Reward, Reward, AreIdeal]:
    (ideal_source_reward, ideal_target_reward, ideal_head_reward) = ideal_reward
    (actual_source_reward, actual_target_reward, actual_head_reward) = actual_reward

    are_ideal = (
        actual_source_reward == ideal_source_reward,
        actual_target_reward == ideal_target_reward,
        actual_head_reward == ideal_head_reward,
    )

    return pubkey, ideal_reward, actual_reward, are_ideal
