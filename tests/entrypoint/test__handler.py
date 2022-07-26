from pathlib import Path
from typing import Optional
from eth_validator_watcher.entrypoint import _handler
from typer import BadParameter
from pytest import raises
from eth_validator_watcher import entrypoint
from sseclient import Event
import json
from os import environ
from freezegun import freeze_time

from eth_validator_watcher.utils import Slack


def test_slack_token_not_defined() -> None:
    with raises(BadParameter):
        _handler(
            beacon_url="",
            pubkeys_file_path=None,
            web3signer_url=None,
            slack_channel="MY SLACK CHANNEL",
            liveness_file=None,
        )


@freeze_time("2023-01-01 00:00:00", auto_tick_seconds=15)
def test_nominal() -> None:
    def get(*args, **kwargs) -> str:
        assert args == ("http://localhost:5052/eth/v1/events",)
        assert kwargs == dict(
            stream=True,
            params=dict(topics="block"),
            headers=dict(Accept="text/event-stream"),
        )

        return "OK"

    class SSEClient:
        def __init__(self, response: str) -> None:
            assert response == "OK"

        def events(self) -> list[Event]:
            return [
                Event(data=json.dumps(dict(slot=63))),
                Event(data=json.dumps(dict(slot=64))),
            ]

    class Beacon:
        def __init__(self, url: str) -> None:
            assert url == "http://localhost:5052"

        def get_active_index_to_pubkey(self, pubkeys: set[str]) -> dict[int, str]:
            assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}

            return {0: "0xaaa", 2: "0xccc", 4: "0xeee"}

        def get_pending_index_to_pubkey(self, pubkeys: set[str]) -> dict[int, str]:
            assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}

            return {1: "0xbbb", 3: "0xddd"}

        def get_potential_block(self, slot: int) -> Optional[str]:
            assert slot in {63, 64}
            return "A BLOCK"

    class Web3Signer:
        def __init__(self, url: str) -> None:
            assert url == "http://localhost:9000"

    class Coinbase:
        nb_calls = 0

        @classmethod
        def emit_eth_usd_conversion_rate(cls) -> None:
            cls.nb_calls += 1

    def get_our_pubkeys(pubkeys_file_path: Path, web3signer: Web3Signer) -> set[str]:
        assert pubkeys_file_path == Path("/path/to/pubkeys")
        assert isinstance(web3signer, Web3Signer)

        return {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}

    def process_missed_attestations(
        beacon: Beacon, index_to_pubkey: dict[int, str], epoch: int
    ) -> set[int]:
        assert isinstance(beacon, Beacon)
        assert index_to_pubkey == {0: "0xaaa", 2: "0xccc", 4: "0xeee"}
        assert epoch == 1

        return {0, 4}

    def process_double_missed_attestations(
        indexes_that_missed_attestation: set[int],
        indexes_that_previously_missed_attestation: set[int],
        index_to_pubkey: dict[int, str],
        epoch: int,
        slack: Slack,
    ) -> set[int]:
        assert indexes_that_missed_attestation == {0, 4}
        assert indexes_that_previously_missed_attestation == set()
        assert index_to_pubkey == {0: "0xaaa", 2: "0xccc", 4: "0xeee"}
        assert epoch == 1
        assert isinstance(slack, Slack)

        return {4}

    def process_future_blocks_proposal(
        beacon: Beacon, pubkeys: set[str], slot: int, is_new_epoch: bool
    ) -> int:
        assert isinstance(beacon, Beacon)
        assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}
        assert slot in {63, 64}
        assert is_new_epoch is True

        return 1

    def process_suboptimal_attestations(
        beacon: Beacon,
        potential_block: Optional[str],
        slot: int,
        index_to_pubkey: dict[int, str],
    ) -> set[int]:
        assert isinstance(beacon, Beacon)
        assert potential_block == "A BLOCK"
        assert slot in {63, 64}
        assert index_to_pubkey == {0: "0xaaa", 2: "0xccc", 4: "0xeee"}

        return {0}

    def process_missed_blocks(
        beacon: Beacon,
        potential_block: Optional[str],
        slot: int,
        previous_slot: Optional[int],
        pubkeys: set[str],
        slack: Slack,
    ) -> None:
        assert isinstance(beacon, Beacon)
        assert potential_block == "A BLOCK"
        assert slot in {63, 64}
        assert previous_slot in {None, 63}
        assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee"}
        assert isinstance(slack, Slack)

    def write_liveness_file(liveness_file: Path) -> None:
        assert liveness_file == Path("/path/to/liveness")

    original_get = entrypoint.requests.get
    entrypoint.requests.get = get  # type: ignore
    entrypoint.SSEClient = SSEClient
    entrypoint.Beacon = Beacon  # type: ignore
    entrypoint.Coinbase = Coinbase  # type: ignore
    entrypoint.Web3Signer = Web3Signer  # type: ignore
    entrypoint.get_our_pubkeys = get_our_pubkeys  # type: ignore
    entrypoint.process_missed_attestations = process_missed_attestations  # type: ignore

    entrypoint.process_double_missed_attestations = (
        process_double_missed_attestations  # type:ignore
    )

    entrypoint.process_future_blocks_proposal = process_future_blocks_proposal  # type: ignore
    entrypoint.process_suboptimal_attestations = process_suboptimal_attestations  # type: ignore
    entrypoint.process_missed_blocks = process_missed_blocks  # type: ignore
    entrypoint.write_liveness_file = write_liveness_file  # type: ignore

    environ["SLACK_TOKEN"] = "my_slack_token"

    _handler(
        beacon_url="http://localhost:5052",
        pubkeys_file_path=Path("/path/to/pubkeys"),
        web3signer_url="http://localhost:9000",
        slack_channel="my slack channel",
        liveness_file=Path("/path/to/liveness"),
    )

    entrypoint.requests.get = original_get

    assert Coinbase.nb_calls == 2
