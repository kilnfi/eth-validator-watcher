from eth_validator_watcher.suboptimal_attestations import (
    process_suboptimal_attestations,
    suboptimal_attestations_rate_gauge,
)

from eth_validator_watcher import suboptimal_attestations


def aggregate_attestations(
    block: str,
    slot: int,
) -> dict[int, list[bool]]:
    assert block == "A dummy block"
    assert slot == 41

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


def test_our_pubkeys():
    """
    In this test case, our pubkeys are "0xaaa" ==> "0xggg".
    Only "0xaaa", "0xccc", "0xeee" & "0xggg" are active.
    Respective validators index are 10, 30, 50, 70.

    "0ccc (30)" and "0xeee (50)" performed optimally during the current epoch.
    "0xaaa (10)" and "0xggg (70)" did not perform optimally during the current epoch.
    """

    class Beacon:
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

    suboptimal_attestations.aggregate_attestations = aggregate_attestations

    assert process_suboptimal_attestations(
        beacon=Beacon(),  # type: ignore
        block="A dummy block",  # type: ignore
        slot=42,
        our_active_validators_index_to_pubkey={
            10: "0xaaa",
            30: "0xccc",
            50: "0xeee",
            70: "0xggg",
        },
    ) == {10, 70}

    assert suboptimal_attestations_rate_gauge.collect()[0].samples[0].value == 50.0  # type: ignore
