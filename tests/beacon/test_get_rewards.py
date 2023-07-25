import json
from pathlib import Path

from pytest import raises
from requests import Response
from requests.exceptions import RetryError
from requests_mock import Mocker

from eth_validator_watcher.beacon import Beacon, NoBlockError
from tests.beacon import assets
from eth_validator_watcher.models import Rewards


def test_get_rewards() -> None:
    rewards_path = Path(assets.__file__).parent / "rewards.json"

    with rewards_path.open() as file_descriptor:
        rewards_dict = json.load(file_descriptor)

    beacon = Beacon("http://beacon-node:5052")

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

        assert beacon.get_rewards(42, {8499, 8500}) == expected
