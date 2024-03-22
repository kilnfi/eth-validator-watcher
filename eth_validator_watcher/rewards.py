"""Contains functions to handle rewards calculation"""

from typing import Tuple

from prometheus_client import Counter, Gauge

from eth_validator_watcher.utils import LimitedDict

from .beacon import Beacon
from .models import BeaconType, Validators

Validator = Validators.DataItem.Validator

Reward = Tuple[int, int, int]  # source, target, head
AreIdeal = Tuple[bool, bool, bool]  # source, target, head

# Network validators
# ------------------
(
    metric_net_suboptimal_sources_rate_gauge,
    metric_net_suboptimal_targets_rate_gauge,
    metric_net_suboptimal_heads_rate_gauge,
) = (
    Gauge("net_suboptimal_sources_rate", "Network suboptimal sources rate"),
    Gauge("net_suboptimal_targets_rate", "Network suboptimal targets rate"),
    Gauge("net_suboptimal_heads_rate", "Network suboptimal heads rate"),
)

(
    metric_net_ideal_sources_count,
    metric_net_ideal_targets_count,
    metric_net_ideal_heads_count,
) = (
    Counter("net_ideal_sources_count", "Network ideal sources count"),
    Counter("net_ideal_targets_count", "Network ideal targets count"),
    Counter("net_ideal_heads_count", "Network ideal heads count"),
)

(
    metric_net_actual_pos_sources_count,
    metric_net_actual_neg_sources_count,
    metric_net_actual_pos_targets_count,
    metric_net_actual_neg_targets_count,
    metric_net_actual_heads_count,
) = (
    Counter("net_actual_pos_sources_count", "Network actual positive sources count"),
    Counter("net_actual_neg_sources_count", "Network actual negative sources count"),
    Counter("net_actual_pos_targets_count", "Network actual positive targets count"),
    Counter("net_actual_neg_targets_count", "Network actual negative targets count"),
    Counter("net_actual_heads_count", "Network actual heads count"),
)

# Our validators
# --------------
(
    metric_our_suboptimal_sources_rate_gauge,
    metric_our_suboptimal_targets_rate_gauge,
    metric_our_suboptimal_heads_rate_gauge,
    key_suboptimal_sources_rate_gauge,
    key_suboptimal_targets_rate_gauge,
    key_suboptimal_heads_rate_gauge,
) = (
    Gauge("our_suboptimal_sources_rate", "Our suboptimal sources rate"),
    Gauge("our_suboptimal_targets_rate", "Our suboptimal targets rate"),
    Gauge("our_suboptimal_heads_rate", "Our suboptimal heads rate"),
    Gauge("key_suboptimal_sources_rate", "Key suboptimal sources rate", ["pubkey"]),
    Gauge("key_suboptimal_targets_rate", "Key suboptimal targets rate", ["pubkey"]),
    Gauge("key_suboptimal_heads_rate", "Key suboptimal heads rate", ["pubkey"]),
)

(
    metric_our_ideal_sources_count,
    metric_our_ideal_targets_count,
    metric_our_ideal_heads_count,
    key_ideal_sources_count,
    key_ideal_targets_count,
    key_ideal_heads_count,
) = (
    Counter("our_ideal_sources_count", "Our ideal sources count"),
    Counter("our_ideal_targets_count", "Our ideal targets count"),
    Counter("our_ideal_heads_count", "Our ideal heads count"),
    Counter("key_ideal_sources_count", "Key ideal sources count", ["pubkey"]),
    Counter("key_ideal_targets_count", "Key ideal targets count", ["pubkey"]),
    Counter("key_ideal_heads_count", "Key ideal heads count", ["pubkey"]),
)

(
    metric_our_actual_pos_sources_count,
    metric_our_actual_neg_sources_count,
    metric_our_actual_pos_targets_count,
    metric_our_actual_neg_targets_count,
    metric_our_actual_heads_count,
    key_actual_pos_sources_count,
    key_actual_neg_sources_count,
    key_actual_pos_targets_count,
    key_actual_neg_targets_count,
    key_actual_heads_count,
) = (
    Counter("our_actual_pos_sources_count", "Our actual positive sources count"),
    Counter("our_actual_neg_sources_count", "Our actual negative sources count"),
    Counter("our_actual_pos_targets_count", "Our actual positive targets count"),
    Counter("our_actual_neg_targets_count", "Our actual negative targets count"),
    Counter("our_actual_heads_count", "Our actual heads count"),
    Counter("key_actual_pos_sources_count", "Key actual positive sources count", ["pubkey"]),
    Counter("key_actual_neg_sources_count", "Key actual negative sources count", ["pubkey"]),
    Counter("key_actual_pos_targets_count", "Key actual positive targets count", ["pubkey"]),
    Counter("key_actual_neg_targets_count", "Key actual negative targets count", ["pubkey"]),
    Counter("key_actual_heads_count", "Key actual heads count", ["pubkey"]),
)

initialized_keys : set[str] = set()

def _log(
    pubkeys: Tuple[str],
    are_ideal: Tuple[bool],
    suboptimal_rate: float,
    epoch: int,
    picto: str,
    label: str,
) -> None:
    not_perfect_pubkeys = {
        pubkey for (pubkey, perfect) in zip(pubkeys, are_ideal) if not perfect
    }

    if len(not_perfect_pubkeys) > 0:
        first_not_perfect_pubkeys = sorted(not_perfect_pubkeys)[:5]

        short_first_not_perfect_pubkeys = [
            pubkey[:10] for pubkey in first_not_perfect_pubkeys
        ]

        short_first_not_perfect_pubkeys_str = ", ".join(short_first_not_perfect_pubkeys)

        diff = len(not_perfect_pubkeys) - len(first_not_perfect_pubkeys)

        print(
            f"{picto} Our validator {short_first_not_perfect_pubkeys_str} and {diff} "
            f"more had not ideal rewards on {label} at epoch {epoch-2} "
            f"({suboptimal_rate:.2%})"
        )


def process_rewards(
    beacon: Beacon,
    beacon_type: BeaconType,
    epoch: int,
    net_epoch_to_index_to_validator: LimitedDict,
    our_epoch_to_index_to_validator: LimitedDict,
    _initialized_keys: set[str],
) -> None:
    """Process rewards for given epoch and validators

    Parameters:
        beacon (Beacon): Beacon object
        beacon_type (BeaconType): Beacon type
        epoch (int): Epoch number

        net_epoch_to_index_to_validator : Limited dictionary with:
            outer key             : epoch
            outer value, inner key: validator indexes
            inner value           : validators

        our_epoch_to_index_to_validator : Limited dictionary with:
            outer key             : epoch
            outer value, inner key: validator indexes
            inner value           : validators
    """

    if epoch < 2:
        return

    if len(_initialized_keys) > 0:
        for pubkey in _initialized_keys:
            if pubkey in initialized_keys:
                continue
            key_suboptimal_sources_rate_gauge.labels(pubkey=pubkey)
            key_suboptimal_targets_rate_gauge.labels(pubkey=pubkey)
            key_suboptimal_heads_rate_gauge.labels(pubkey=pubkey)
            key_ideal_sources_count.labels(pubkey=pubkey)
            key_ideal_targets_count.labels(pubkey=pubkey)
            key_ideal_heads_count.labels(pubkey=pubkey)
            key_actual_pos_sources_count.labels(pubkey=pubkey)
            key_actual_neg_sources_count.labels(pubkey=pubkey)
            key_actual_pos_targets_count.labels(pubkey=pubkey)
            key_actual_neg_targets_count.labels(pubkey=pubkey)
            key_actual_heads_count.labels(pubkey=pubkey)

            initialized_keys.add(pubkey)

        for initialized_key in initialized_keys:
            if initialized_key not in _initialized_keys:
                key_suboptimal_sources_rate_gauge.remove(pubkey=initialized_key)
                key_suboptimal_targets_rate_gauge.remove(pubkey=initialized_key)
                key_suboptimal_heads_rate_gauge.remove(pubkey=initialized_key)
                key_ideal_sources_count.remove(pubkey=initialized_key)
                key_ideal_targets_count.remove(pubkey=initialized_key)
                key_ideal_heads_count.remove(pubkey=initialized_key)
                key_actual_pos_sources_count.remove(pubkey=initialized_key)
                key_actual_neg_sources_count.remove(pubkey=initialized_key)
                key_actual_pos_targets_count.remove(pubkey=initialized_key)
                key_actual_neg_targets_count.remove(pubkey=initialized_key)
                key_actual_heads_count.remove(pubkey=initialized_key)

                initialized_keys.remove(initialized_key)


    # Network validators
    # ------------------
    net_index_to_validator = (
        net_epoch_to_index_to_validator[epoch - 2]
        if epoch - 2 in net_epoch_to_index_to_validator
        else (
            net_epoch_to_index_to_validator[epoch - 1]
            if epoch - 1 in net_epoch_to_index_to_validator
            else net_epoch_to_index_to_validator[epoch]
        )
    )

    if len(net_index_to_validator) == 0:
        return

    data = beacon.get_rewards(beacon_type, epoch - 2).data

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
        for index, validator in net_index_to_validator.items()
        if index in index_to_actual_reward
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

    metric_net_ideal_sources_count.inc(total_ideal_sources)
    metric_net_ideal_targets_count.inc(total_ideal_targets)
    metric_net_ideal_heads_count.inc(total_ideal_heads)

    total_actual_sources = sum(actual_sources)
    total_actual_targets = sum(actual_targets)
    total_actual_heads = sum(actual_heads)

    (
        metric_net_actual_pos_sources_count
        if total_actual_sources >= 0
        else metric_net_actual_neg_sources_count
    ).inc(abs(total_actual_sources))

    (
        metric_net_actual_pos_targets_count
        if total_actual_targets >= 0
        else metric_net_actual_neg_targets_count
    ).inc(abs(total_actual_targets))

    metric_net_actual_heads_count.inc(total_actual_heads)


    if len(initialized_keys) > 0:
        for pubkey in zip(pubkeys, ideal_sources, ideal_targets, ideal_heads):
            if pubkey not in initialized_keys:
                continue
            key_ideal_sources_count.labels(pubkey=pubkey).inc(ideal_sources)
            key_ideal_targets_count.labels(pubkey=pubkey).inc(ideal_targets)
            key_ideal_heads_count.labels(pubkey=pubkey).inc(ideal_heads)

        for pubkey, _actual_sources, _actual_targets, _actual_heads in zip(pubkeys, actual_sources, actual_targets, actual_heads):
            if pubkey not in initialized_keys:
                continue
            (
                key_actual_pos_sources_count.labels(pubkey=pubkey)
                if _actual_sources >= 0
                else key_actual_neg_sources_count.labels(pubkey=pubkey)
            ).inc(abs(_actual_sources))
            (
                key_actual_pos_targets_count.labels(pubkey=pubkey)
                if _actual_targets >= 0
                else key_actual_neg_targets_count.labels(pubkey=pubkey)
            ).inc(abs(_actual_targets))
            key_actual_heads_count.labels(pubkey=pubkey).inc(_actual_heads)

    suboptimal_sources_rate = 1 - sum(are_sources_ideal) / len(are_sources_ideal)
    suboptimal_targets_rate = 1 - sum(are_targets_ideal) / len(are_targets_ideal)
    suboptimal_heads_rate = 1 - sum(are_heads_ideal) / len(are_heads_ideal)

    metric_net_suboptimal_sources_rate_gauge.set(suboptimal_sources_rate)
    metric_net_suboptimal_targets_rate_gauge.set(suboptimal_targets_rate)
    metric_net_suboptimal_heads_rate_gauge.set(suboptimal_heads_rate)

    # Our validators
    # --------------
    our_index_to_validator = (
        our_epoch_to_index_to_validator[epoch - 2]
        if epoch - 2 in our_epoch_to_index_to_validator
        else (
            our_epoch_to_index_to_validator[epoch - 1]
            if epoch - 1 in our_epoch_to_index_to_validator
            else our_epoch_to_index_to_validator[epoch]
        )
    )

    our_indexes = set(our_index_to_validator)

    if len(our_indexes) == 0:
        return

    data = beacon.get_rewards(beacon_type, epoch - 2, our_indexes).data

    effective_balance_to_ideal_reward = {
        reward.effective_balance: (reward.source, reward.target, reward.head)
        for reward in data.ideal_rewards
    }

    index_to_actual_reward = {
        reward.validator_index: (reward.source, reward.target, reward.head)
        for reward in data.total_rewards
    }

    items = [
        _process_validator(
            validator.pubkey,
            effective_balance_to_ideal_reward[validator.effective_balance],
            index_to_actual_reward[index],
        )
        for index, validator in our_index_to_validator.items()
    ]

    unzipped = zip(*items)  # type: ignore

    pubkeys, ideal_rewards, actual_rewards, ideals = unzipped

    ideal_sources, ideal_targets, ideal_heads = zip(*ideal_rewards)
    actual_sources, actual_targets, actual_heads = zip(*actual_rewards)
    are_sources_ideal, are_targets_ideal, are_heads_ideal = zip(*ideals)

    total_ideal_sources = sum(ideal_sources)
    total_ideal_targets = sum(ideal_targets)
    total_ideal_heads = sum(ideal_heads)

    metric_our_ideal_sources_count.inc(total_ideal_sources)
    metric_our_ideal_targets_count.inc(total_ideal_targets)
    metric_our_ideal_heads_count.inc(total_ideal_heads)

    if len(initialized_keys) > 0:
        for pubkey, ideal_sources in zip(pubkeys, ideal_sources):
            key_ideal_sources_count.labels(pubkey).inc(ideal_sources)
        for pubkey, ideal_targets in zip(pubkeys, ideal_targets):
            key_ideal_targets_count.labels(pubkey).inc(ideal_targets)
        for pubkey, ideal_heads in zip(pubkeys, ideal_heads):
            key_ideal_heads_count.labels(pubkey).inc(ideal_heads)

    total_actual_sources = sum(actual_sources)
    total_actual_targets = sum(actual_targets)
    total_actual_heads = sum(actual_heads)

    (
        metric_our_actual_pos_sources_count
        if total_actual_sources >= 0
        else metric_our_actual_neg_sources_count
    ).inc(abs(total_actual_sources))

    (
        metric_our_actual_pos_targets_count
        if total_actual_targets >= 0
        else metric_our_actual_neg_targets_count
    ).inc(abs(total_actual_targets))

    metric_our_actual_heads_count.inc(total_actual_heads)

    suboptimal_sources_rate = 1 - sum(are_sources_ideal) / len(are_sources_ideal)
    suboptimal_targets_rate = 1 - sum(are_targets_ideal) / len(are_targets_ideal)
    suboptimal_heads_rate = 1 - sum(are_heads_ideal) / len(are_heads_ideal)

    metric_our_suboptimal_sources_rate_gauge.set(suboptimal_sources_rate)
    metric_our_suboptimal_targets_rate_gauge.set(suboptimal_targets_rate)
    metric_our_suboptimal_heads_rate_gauge.set(suboptimal_heads_rate)

    if len(initialized_keys) > 0:
        for pubkey in pubkeys:
            _sum = 0
            _cnt = 0
            for _pubkey, _are_sources_ideal in zip(pubkeys, are_sources_ideal):
                if _pubkey == pubkey:
                    _sum += _are_sources_ideal
                    _cnt += 1
            key_suboptimal_sources_rate_gauge.labels(pubkey).set(_sum / _cnt)

        for pubkey in pubkeys:
            _sum = 0
            _cnt = 0
            for _pubkey, _are_targets_ideal in zip(pubkeys, are_targets_ideal):
                if _pubkey == pubkey:
                    _sum += _are_targets_ideal
                    _cnt += 1
            key_suboptimal_targets_rate_gauge.labels(pubkey).set(_sum / _cnt)

        for pubkey in pubkeys:
            _sum = 0
            _cnt = 0
            for _pubkey, _are_heads_ideal in zip(pubkeys, are_heads_ideal):
                if _pubkey == pubkey:
                    _sum += _are_heads_ideal
                    _cnt += 1
            key_suboptimal_heads_rate_gauge.labels(pubkey).set(_sum / _cnt)


    _log(pubkeys, are_sources_ideal, suboptimal_sources_rate, epoch, "🚰", "source")
    _log(pubkeys, are_targets_ideal, suboptimal_targets_rate, epoch, "🎯", "target")
    _log(pubkeys, are_heads_ideal, suboptimal_heads_rate, epoch, "👤", "head ")


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
