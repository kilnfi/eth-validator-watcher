from eth_validator_watcher.missed_attestations import (
    handle_missed_attestation_detection,
)
from eth_validator_watcher.models import DataBlock
from prometheus_client import Gauge


def test_no_our_pubkeys():
    number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge = Gauge("a0", "a0")
    rate_of_not_optimal_attestation_inclusion_gauge = Gauge("a1", "a1")

    class Beacon:
        pass

    assert handle_missed_attestation_detection(
        beacon=Beacon(),
        data_block=DataBlock(slot=42),
        our_pubkeys=set(),
        our_active_val_index_to_pubkey=None,
        cumulated_our_ko_vals_index={},
        cumulated_or_2_times_in_a_raw_vals_index={},
        number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge=number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge,
        rate_of_not_optimal_attestation_inclusion_gauge=rate_of_not_optimal_attestation_inclusion_gauge,
    ) == ({}, set(), set())


def test_our_pubkeys():
    """
    In this test case, our pubkeys are "0xaaa" ==> "0xggg".
    Only "0xaaa", "0xccc", "0xeee" & "0xggg" are active.
    Respective validators index are 10, 30, 50, 70.

    "0xaaa (10)" and "0xccc (30)" did not performed optimally on the previous epoch.
    "0xccc (30)" did not performed optimally on the second previous epoch.

    "0ccc (30)" and "0xeee (50)" perform optimally on the current epoch.
    "0xaaa (10)" and "0xggg (70)" do no perform optimally on the current epoch.
    (==> 0xaaa (10) performed 2 times in a raw non optimally)
    """

    number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge = Gauge("ab", "b0")
    rate_of_not_optimal_attestation_inclusion_gauge = Gauge("b1", "b1")

    our_pubkeys = {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee", "0xfff", "0xggg"}

    class Beacon:
        @staticmethod
        def get_active_validator_index_to_pubkey(
            pubkeys: set[str],
        ) -> dict[int, str]:
            assert pubkeys == our_pubkeys

            return {
                10: "0xaaa",
                30: "0xccc",
                50: "0xeee",
                70: "0xggg",
            }

        @staticmethod
        def get_duty_slot_to_committee_index_to_validators_index(
            epoch: int,
        ) -> dict[int, dict[int, list[int]]]:
            assert epoch == 1

            return {
                41: {
                    0: [
                        1,  # Not our key
                        2,  # Not our key
                        3,  # Not our key
                        4,  # Not our key
                        5,  # Not our key
                        6,  # Not our key
                        7,  # Not our key
                        8,  # Not our key
                        9,  # Not our key
                        10,  # 0xaaa
                        11,  # Not our key
                        29,  # Not our key
                        30,  # 0xccc
                        31,  # Not our key
                        32,  # Not our key
                        33,  # Not our key
                        34,  # Not our key
                        35,  # Not our key
                    ],
                    1: [
                        47,  # Not our key
                        48,  # Not our key
                        49,  # Not our key
                        50,  # 0xeee
                        51,  # Not our key
                        69,  # Not our key
                        70,  # 0xfff
                        71,  # Not our key
                        72,  # Not our key
                        73,  # Not our key
                        74,  # Not our key
                        75,  # Not our key
                        76,  # Not our key
                        77,  # Not our key
                        78,  # Not our key
                        79,  # Not our key
                        80,  # Not our key
                        81,  # Not our key
                    ],
                }
            }

        @staticmethod
        def aggregate_attestations_from_previous_slot(
            slot: int,
        ) -> dict[int, list[bool]]:
            assert slot == 42

            return {
                0: [
                    False,  # Not our key
                    True,  # Not our key
                    False,  #  Not our key
                    True,  # Not our key
                    False,  # Not our key
                    True,  #  Not our key
                    False,  # Not our key
                    True,  #  Not our key
                    False,  #  Not our key
                    False,  # 0xaaa (validator index 10)
                    False,  # Not our key
                    True,  # Not our key
                    True,  # 0xccc (validator index 30)
                    False,  #  Not our key
                    False,  #  Not our key
                    True,  #  Not our key
                    False,  # Not our key
                    False,  # Not our key
                ],
                1: [
                    False,  # Not our key
                    True,  # Not our key
                    False,  #  Not our key
                    True,  # 0xeee (validator index 50)
                    False,  # Not our key
                    True,  #  Not our key
                    False,  # 0xggg (validator index 70)
                    True,  #  Not our key
                    False,  #  Not our key
                    False,  #  Not our key
                    False,  # Not our key
                    True,  # Not our key
                    True,  #  Not our key
                    False,  #  Not our key
                    False,  #  Not our key
                    True,  #  Not our key
                    False,  # Not our key
                    False,  # Not our key
                ],
            }

    assert handle_missed_attestation_detection(
        beacon=Beacon(),
        data_block=DataBlock(slot=42),
        our_pubkeys=our_pubkeys,
        our_active_val_index_to_pubkey=None,
        cumulated_our_ko_vals_index={10, 30},
        cumulated_or_2_times_in_a_raw_vals_index={30},
        number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge=number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge,
        rate_of_not_optimal_attestation_inclusion_gauge=rate_of_not_optimal_attestation_inclusion_gauge,
    ) == (
        {  # Mapping from our validator active validators index to pubkey
            10: "0xaaa",
            30: "0xccc",
            50: "0xeee",
            70: "0xggg",
        },
        {10, 70},  # Keys which perform suboptimally this time
        {10},  # Keys which perform suboptimally 2 epochs in a raw
    )

    assert (
        number_of_two_not_optimal_attestation_inclusion_in_a_raw_gauge.collect()[0]
        .samples[0]
        .value
        == 1
    )

    assert (
        rate_of_not_optimal_attestation_inclusion_gauge.collect()[0].samples[0].value
        == 50.0
    )
