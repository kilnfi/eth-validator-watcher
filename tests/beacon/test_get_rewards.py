import json
from pathlib import Path

from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon
from eth_validator_watcher.models import BeaconType, Rewards
from tests.beacon import assets


def test_get_rewards_not_supported() -> None:
    beacon = Beacon("http://beacon-node:5052", 90)

    expected = Rewards(data=Rewards.Data(ideal_rewards=[], total_rewards=[]))

    actual = beacon.get_rewards(BeaconType.OLD_PRYSM, 42, {8499, 8500})
    assert expected == actual

    actual = beacon.get_rewards(BeaconType.NIMBUS, 42, {8499, 8500})
    assert expected == actual


def test_get_rewards() -> None:
    rewards_path = Path(assets.__file__).parent / "rewards.json"

    with rewards_path.open() as file_descriptor:
        rewards_dict = json.load(file_descriptor)

    beacon = Beacon("http://beacon-node:5052", 90)

    def match_request(request) -> bool:
        return request.json() == ["8499", "8500"]

    expected = Rewards(
        data=Rewards.Data(
            ideal_rewards=[
                Rewards.Data.IdealReward(
                    effective_balance=31000000000, head=2856, target=5511, source=2966
                ),
                Rewards.Data.IdealReward(
                    effective_balance=32000000000, head=2948, target=5689, source=3062
                ),
            ],
            total_rewards=[
                Rewards.Data.TotalReward(
                    validator_index=8499, head=2948, target=5689, source=3062
                ),
                Rewards.Data.TotalReward(
                    validator_index=8500, head=0, target=-5707, source=-3073
                ),
            ],
        )
    )

    with Mocker() as mock:
        mock.post(
            f"http://beacon-node:5052/eth/v1/beacon/rewards/attestations/42",
            additional_matcher=match_request,
            json=rewards_dict,
        )

        assert beacon.get_rewards(BeaconType.LIGHTHOUSE, 42, {8499, 8500}) == expected
