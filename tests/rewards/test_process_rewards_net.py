from math import isclose
from typing import Optional

from eth_validator_watcher.models import BeaconType, Rewards, Validators
from eth_validator_watcher.rewards import (
    net_ideal_sources_count,
    net_ideal_targets_count,
    net_ideal_heads_count,
    net_actual_neg_sources_count,
    net_actual_pos_sources_count,
    net_actual_neg_targets_count,
    net_actual_pos_targets_count,
    net_actual_heads_count,
    net_suboptimal_sources_rate_gauge,
    net_suboptimal_targets_rate_gauge,
    net_suboptimal_heads_rate_gauge,
    process_rewards,
)
from eth_validator_watcher.utils import LimitedDict

Validator = Validators.DataItem.Validator


def test_process_rewards_low_epoch() -> None:
    for epoch in 0, 1:
        # We just want to be sure it doesn't raise an exception.

        process_rewards(
            BeaconType.LIGHTHOUSE,  # type: ignore
            "a beacon",  # type: ignore
            epoch,
            LimitedDict(2),
            LimitedDict(2),
        )


def test_process_rewards_no_network_validator() -> None:
    net_epoch_to_index_to_validator = LimitedDict(2)
    net_epoch_to_index_to_validator[42] = {}

    process_rewards(
        BeaconType.LIGHTHOUSE,  # type: ignore
        "a beacon",  # type: ignore
        42,
        net_epoch_to_index_to_validator,
        LimitedDict(2),
    )


def test_process_rewards_all_net_validators_are_ideal() -> None:
    class Beacon:
        def get_rewards(
            self,
            beacon_type: BeaconType,
            epoch: int,
            validators_index: Optional[set[int]] = None,
        ) -> Rewards:
            assert isinstance(beacon_type, BeaconType)
            assert epoch == 40
            assert validators_index is None

            return Rewards(
                data=Rewards.Data(
                    ideal_rewards=[
                        Rewards.Data.IdealReward(
                            effective_balance=31_000_000_000,
                            head=2_856,
                            target=5_511,
                            source=2_966,
                        ),
                        Rewards.Data.IdealReward(
                            effective_balance=32_000_000_000,
                            head=2_948,
                            target=5_689,
                            source=3_062,
                        ),
                    ],
                    total_rewards=[
                        Rewards.Data.TotalReward(  # 32 ETH
                            validator_index=1, source=3_062, target=5_689, head=2_948
                        ),
                        Rewards.Data.TotalReward(  # 31 ETH
                            validator_index=2, source=2_966, target=5_511, head=2_856
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH
                            validator_index=3, source=3_062, target=5_689, head=2_948
                        ),
                    ],
                )
            )

    beacon = Beacon()

    ideal_sources_count_before = net_ideal_sources_count.collect()[0].samples[0].value  # type: ignore
    ideal_targets_count_before = net_ideal_targets_count.collect()[0].samples[0].value  # type: ignore
    ideal_heads_count_before = net_ideal_heads_count.collect()[0].samples[0].value  # type: ignore

    actual_positive_sources_count_before = net_actual_pos_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_sources_count_before = net_actual_neg_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_positive_targets_count_before = net_actual_pos_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_targets_count_before = net_actual_neg_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_heads_count_before = net_actual_heads_count.collect()[0].samples[0].value  # type: ignore

    net_epoch_to_index_to_validator = LimitedDict(2)
    net_epoch_to_index_to_validator[42] = {
        1: Validator(
            pubkey="0x111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        2: Validator(
            pubkey="0x222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222",
            effective_balance=31_000_000_000,
            slashed=False,
        ),
        3: Validator(
            pubkey="0x333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
    }

    our_epoch_to_index_to_validator = LimitedDict(2)
    our_epoch_to_index_to_validator[42] = {}

    process_rewards(
        beacon,  # type: ignore
        BeaconType.LIGHTHOUSE,
        42,
        net_epoch_to_index_to_validator,
        our_epoch_to_index_to_validator,
    )

    ideal_sources_count_after = net_ideal_sources_count.collect()[0].samples[0].value  # type: ignore
    ideal_targets_count_after = net_ideal_targets_count.collect()[0].samples[0].value  # type: ignore
    ideal_heads_count_after = net_ideal_heads_count.collect()[0].samples[0].value  # type: ignore

    actual_positive_sources_count_after = net_actual_pos_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_sources_count_after = net_actual_neg_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_positive_targets_count_after = net_actual_pos_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_targets_count_after = net_actual_neg_targets_count.collect()[0].samples[0].value  # type: ignore

    actual_heads_count_after = net_actual_heads_count.collect()[0].samples[0].value  # type: ignore

    assert ideal_sources_count_after - ideal_sources_count_before == 9_090
    assert ideal_targets_count_after - ideal_targets_count_before == 16_889
    assert ideal_heads_count_after - ideal_heads_count_before == 8_752

    assert (
        actual_positive_sources_count_after - actual_positive_sources_count_before
        == 9_090
    )

    assert (
        actual_negative_sources_count_after - actual_negative_sources_count_before == 0
    )

    assert (
        actual_positive_targets_count_after - actual_positive_targets_count_before
        == 16_889
    )

    assert (
        actual_negative_targets_count_after - actual_negative_targets_count_before == 0
    )

    assert actual_heads_count_after - actual_heads_count_before == 8_752

    assert isclose(net_suboptimal_sources_rate_gauge.collect()[0].samples[0].value, 0.0)  # type: ignore
    assert isclose(net_suboptimal_targets_rate_gauge.collect()[0].samples[0].value, 0.0)  # type: ignore
    assert isclose(net_suboptimal_heads_rate_gauge.collect()[0].samples[0].value, 0.0)  # type: ignore


def test_process_rewards_some_net_validators_are_ideal() -> None:
    """10 validators.
    5 are perfect.
    2 have good source, good target but wrong head.
    2 have good source, but wrong target and wrong head.
    1 has wrong source, wrong target and wrong head.
    """

    class Beacon:
        def get_rewards(
            self,
            beacon_type: BeaconType,
            epoch: int,
            validators_index: Optional[set[int]] = None,
        ) -> Rewards:
            assert isinstance(beacon_type, BeaconType)
            assert epoch == 40
            assert validators_index is None

            return Rewards(
                data=Rewards.Data(
                    ideal_rewards=[
                        Rewards.Data.IdealReward(
                            effective_balance=31_000_000_000,
                            source=2_966,
                            target=5_511,
                            head=2_856,
                        ),
                        Rewards.Data.IdealReward(
                            effective_balance=32_000_000_000,
                            source=3_062,
                            target=5_689,
                            head=2_948,
                        ),
                    ],
                    total_rewards=[
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, GH
                            validator_index=1, source=3_062, target=5_689, head=2_948
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, GH
                            validator_index=2, source=3_062, target=5_689, head=2_948
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, GH
                            validator_index=3, source=3_062, target=5_689, head=2_948
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, GH
                            validator_index=4, source=3_062, target=5_689, head=2_948
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, GH
                            validator_index=5, source=3_062, target=5_689, head=2_948
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, BH
                            validator_index=6, source=3_062, target=5_689, head=0
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, GT, BH
                            validator_index=7, source=3_062, target=5_689, head=0
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - GS, BT, BH
                            validator_index=8, source=3_062, target=-5_707, head=0
                        ),
                        Rewards.Data.TotalReward(  # 31 ETH - GS, BT, BH
                            validator_index=9, source=2_966, target=-5_600, head=0
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH - BS, BT, BH
                            validator_index=10, source=-3_073, target=-5_707, head=0
                        ),
                    ],
                )
            )

    beacon = Beacon()

    ideal_sources_count_before = net_ideal_sources_count.collect()[0].samples[0].value  # type: ignore
    ideal_targets_count_before = net_ideal_targets_count.collect()[0].samples[0].value  # type: ignore
    ideal_heads_count_before = net_ideal_heads_count.collect()[0].samples[0].value  # type: ignore

    actual_positive_sources_count_before = net_actual_pos_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_sources_count_before = net_actual_neg_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_positive_targets_count_before = net_actual_pos_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_targets_count_before = net_actual_neg_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_heads_count_before = net_actual_heads_count.collect()[0].samples[0].value  # type: ignore

    net_epoch_to_index_to_validator = LimitedDict(2)
    net_epoch_to_index_to_validator[42] = {
        1: Validator(
            pubkey="0x111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        2: Validator(
            pubkey="0x222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        3: Validator(
            pubkey="0x333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        4: Validator(
            pubkey="444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        5: Validator(
            pubkey="555555555555555555555555555555555555555555555555555555555555555555555555555555555555555555555555",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        6: Validator(
            pubkey="666666666666666666666666666666666666666666666666666666666666666666666666666666666666666666666666",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        7: Validator(
            pubkey="777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        8: Validator(
            pubkey="888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        9: Validator(
            pubkey="999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            effective_balance=31_000_000_000,
            slashed=False,
        ),
        10: Validator(
            pubkey="000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
    }

    our_epoch_to_index_to_validator = LimitedDict(2)
    our_epoch_to_index_to_validator[42] = {}

    process_rewards(
        beacon,  # type: ignore
        BeaconType.LIGHTHOUSE,
        42,
        net_epoch_to_index_to_validator,
        our_epoch_to_index_to_validator,
    )

    ideal_sources_count_after = net_ideal_sources_count.collect()[0].samples[0].value  # type: ignore
    ideal_targets_count_after = net_ideal_targets_count.collect()[0].samples[0].value  # type: ignore
    ideal_heads_count_after = net_ideal_heads_count.collect()[0].samples[0].value  # type: ignore

    actual_positive_sources_count_after = net_actual_pos_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_sources_count_after = net_actual_neg_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_positive_targets_count_after = net_actual_pos_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_targets_count_after = net_actual_neg_targets_count.collect()[0].samples[0].value  # type: ignore

    actual_heads_count_after = net_actual_heads_count.collect()[0].samples[0].value  # type: ignore

    assert ideal_sources_count_after - ideal_sources_count_before == 30_524
    assert ideal_targets_count_after - ideal_targets_count_before == 56_712
    assert ideal_heads_count_after - ideal_heads_count_before == 29_388

    assert (
        actual_positive_sources_count_after - actual_positive_sources_count_before
        == 24_389
    )

    assert (
        actual_negative_sources_count_after - actual_negative_sources_count_before == 0
    )

    assert (
        actual_positive_targets_count_after - actual_positive_targets_count_before
        == 22_809
    )

    assert (
        actual_negative_targets_count_after - actual_negative_targets_count_before == 0
    )

    assert actual_heads_count_after - actual_heads_count_before == 14_740

    assert isclose(
        net_suboptimal_sources_rate_gauge.collect()[0].samples[0].value,  # type: ignore
        0.1,
    )

    assert isclose(
        net_suboptimal_targets_rate_gauge.collect()[0].samples[0].value,  # type: ignore
        0.3,
    )

    assert isclose(
        net_suboptimal_heads_rate_gauge.collect()[0].samples[0].value,  # type: ignore
        0.5,
    )


def test_process_rewards_no_net_validator_is_ideal() -> None:
    class Beacon:
        def get_rewards(
            self,
            beacon_type: BeaconType,
            epoch: int,
            validators_index: Optional[set[int]] = None,
        ) -> Rewards:
            assert isinstance(beacon_type, BeaconType)
            assert epoch == 40
            assert validators_index == None

            return Rewards(
                data=Rewards.Data(
                    ideal_rewards=[
                        Rewards.Data.IdealReward(
                            effective_balance=31_000_000_000,
                            head=2_856,
                            target=5_511,
                            source=2_966,
                        ),
                        Rewards.Data.IdealReward(
                            effective_balance=32_000_000_000,
                            head=2_948,
                            target=5_689,
                            source=3_062,
                        ),
                    ],
                    total_rewards=[
                        Rewards.Data.TotalReward(  # 32 ETH
                            validator_index=1, source=-9_000, target=-8_000, head=0
                        ),
                        Rewards.Data.TotalReward(  # 31 ETH
                            validator_index=2, source=-8_500, target=-7_500, head=0
                        ),
                        Rewards.Data.TotalReward(  # 32 ETH
                            validator_index=3, source=-9_000, target=-8_000, head=0
                        ),
                    ],
                )
            )

    beacon = Beacon()

    ideal_sources_count_before = net_ideal_sources_count.collect()[0].samples[0].value  # type: ignore
    ideal_targets_count_before = net_ideal_targets_count.collect()[0].samples[0].value  # type: ignore
    ideal_heads_count_before = net_ideal_heads_count.collect()[0].samples[0].value  # type: ignore

    actual_positive_sources_count_before = net_actual_pos_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_sources_count_before = net_actual_neg_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_positive_targets_count_before = net_actual_pos_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_targets_count_before = net_actual_neg_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_heads_count_before = net_actual_heads_count.collect()[0].samples[0].value  # type: ignore

    net_epoch_to_index_to_validator = LimitedDict(2)
    net_epoch_to_index_to_validator[42] = {
        1: Validator(
            pubkey="0x111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
        2: Validator(
            pubkey="0x222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222",
            effective_balance=31_000_000_000,
            slashed=False,
        ),
        3: Validator(
            pubkey="0x333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333",
            effective_balance=32_000_000_000,
            slashed=False,
        ),
    }

    our_epoch_to_index_to_validator = LimitedDict(2)
    our_epoch_to_index_to_validator[42] = {}

    process_rewards(
        beacon,  # type: ignore
        BeaconType.LIGHTHOUSE,
        42,
        net_epoch_to_index_to_validator,
        our_epoch_to_index_to_validator,
    )

    ideal_sources_count_after = net_ideal_sources_count.collect()[0].samples[0].value  # type: ignore
    ideal_targets_count_after = net_ideal_targets_count.collect()[0].samples[0].value  # type: ignore
    ideal_heads_count_after = net_ideal_heads_count.collect()[0].samples[0].value  # type: ignore

    actual_positive_sources_count_after = net_actual_pos_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_sources_count_after = net_actual_neg_sources_count.collect()[0].samples[0].value  # type: ignore
    actual_positive_targets_count_after = net_actual_pos_targets_count.collect()[0].samples[0].value  # type: ignore
    actual_negative_targets_count_after = net_actual_neg_targets_count.collect()[0].samples[0].value  # type: ignore

    actual_heads_count_after = net_actual_heads_count.collect()[0].samples[0].value  # type: ignore

    assert ideal_sources_count_after - ideal_sources_count_before == 9_090
    assert ideal_targets_count_after - ideal_targets_count_before == 16_889
    assert ideal_heads_count_after - ideal_heads_count_before == 8_752

    assert (
        actual_positive_sources_count_after - actual_positive_sources_count_before == 0
    )

    assert (
        actual_negative_sources_count_after - actual_negative_sources_count_before
        == 26_500
    )

    assert (
        actual_positive_targets_count_after - actual_positive_targets_count_before == 0
    )

    assert (
        actual_negative_targets_count_after - actual_negative_targets_count_before
        == 23_500
    )

    assert actual_heads_count_after - actual_heads_count_before == 0

    assert isclose(net_suboptimal_sources_rate_gauge.collect()[0].samples[0].value, 1.0)  # type: ignore
    assert isclose(net_suboptimal_targets_rate_gauge.collect()[0].samples[0].value, 1.0)  # type: ignore
    assert isclose(net_suboptimal_heads_rate_gauge.collect()[0].samples[0].value, 1.0)  # type: ignore
