from os import environ
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from freezegun import freeze_time
from pytest import raises
from typer import BadParameter

from eth_validator_watcher import entrypoint
from eth_validator_watcher.config import WatchedKeyConfig
from eth_validator_watcher.entrypoint import handler, _handler
from eth_validator_watcher.models import BeaconType, Genesis, Validators
from eth_validator_watcher.utils import LimitedDict, Slack
from eth_validator_watcher.web3signer import Web3Signer
from tests.entrypoint import assets

StatusEnum = Validators.DataItem.StatusEnum
Validator = Validators.DataItem.Validator


def test_fee_recipient_set_while_execution_url_not_set() -> None:
    with raises(BadParameter):
        _handler(
            beacon_url="",
            execution_url=None,
            watched_keys=None,
            web3signer_url=None,
            default_fee_recipient="something",
            slack_channel="MY SLACK CHANNEL",
            slack_token=None,
            beacon_type=BeaconType.OLD_TEKU,
            relays_url=[],
            liveness_file=None,
        )


def test_fee_recipient_not_valid() -> None:
    with raises(BadParameter):
        _handler(
            beacon_url="",
            execution_url="http://localhost:8545",
            watched_keys=None,
            web3signer_url=None,
            default_fee_recipient="something",
            slack_channel="MY SLACK CHANNEL",
            slack_token=None,
            beacon_type=BeaconType.OLD_TEKU,
            relays_url=[],
            liveness_file=None,
        )


def test_slack_token_not_defined() -> None:
    with raises(BadParameter):
        _handler(
            beacon_url="",
            execution_url=None,
            watched_keys=None,
            web3signer_url=None,
            default_fee_recipient=None,
            slack_channel="MY SLACK CHANNEL",
            slack_token=None,
            beacon_type=BeaconType.OLD_TEKU,
            relays_url=[],
            liveness_file=None,
        )



def test_chain_not_ready() -> None:
    class Beacon:
        def __init__(self, url: str) -> None:
            assert url == "http://localhost:5052"

        def get_genesis(self) -> Genesis:
            return Genesis(
                data=Genesis.Data(
                    genesis_time=0,
                )
            )

    def get_our_pubkeys(pubkeys_file_path: Path, web3signer: None) -> set[str]:
        return {"0x12345", "0x67890"}

    def slots(genesis_time: int) -> Iterator[Tuple[(int, int)]]:
        assert genesis_time == 0
        yield -32, 1664

    def convert_seconds_to_dhms(seconds: int) -> Tuple[int, int, int, int]:
        assert seconds == 384
        return 42, 42, 42, 42

    def write_liveness_file(liveness_file: Path) -> None:
        assert liveness_file == Path("/path/to/liveness")

    def start_http_server(_: int) -> None:
        pass

    entrypoint.get_our_pubkeys = get_our_pubkeys
    entrypoint.Beacon = Beacon
    entrypoint.slots = slots
    entrypoint.convert_seconds_to_dhms = convert_seconds_to_dhms
    entrypoint.write_liveness_file = write_liveness_file
    entrypoint.start_http_server = start_http_server

    _handler(
        beacon_url="http://localhost:5052",
        execution_url=None,
        watched_keys=None,
        web3signer_url=None,
        default_fee_recipient=None,
        slack_channel=None,
        slack_token=None,
        beacon_type=BeaconType.OLD_TEKU,
        relays_url=[],
        liveness_file=Path("/path/to/liveness"),
    )


@freeze_time("2023-01-01 00:00:00", auto_tick_seconds=15)
def test_nominal() -> None:
    class Beacon:
        def __init__(self, url: str) -> None:
            assert url == "http://localhost:5052"

        def get_genesis(self) -> Genesis:
            return Genesis(
                data=Genesis.Data(
                    genesis_time=0,
                )
            )

        def get_status_to_index_to_validator(
            self,
        ) -> dict[StatusEnum, dict[int, Validator]]:
            return {
                StatusEnum.activeOngoing: {
                    0: Validator(
                        pubkey="0xaaa", effective_balance=32000000000, slashed=False
                    ),
                    2: Validator(
                        pubkey="0xccc", effective_balance=32000000000, slashed=False
                    ),
                    4: Validator(
                        pubkey="0xeee", effective_balance=32000000000, slashed=False
                    ),
                },
                StatusEnum.pendingQueued: {
                    1: Validator(
                        pubkey="0xbbb", effective_balance=32000000000, slashed=False
                    ),
                    3: Validator(
                        pubkey="0xddd", effective_balance=32000000000, slashed=False
                    ),
                },
                StatusEnum.exitedSlashed: {
                    5: Validator(
                        pubkey="0xfff", effective_balance=32000000000, slashed=True
                    ),
                    6: Validator(
                        pubkey="0xggg", effective_balance=32000000000, slashed=True
                    ),
                },
            }

        def get_potential_block(self, slot: int) -> str | None:
            assert slot in {63, 64}
            return "A BLOCK"

    class Coinbase:
        nb_calls = 0

        @classmethod
        def emit_eth_usd_conversion_rate(cls) -> None:
            cls.nb_calls += 1

    class Relays:
        def __init__(self, urls: list[str]) -> None:
            assert urls == ["http://my-awesome-relay.com"]

        def process(self, slot: int) -> None:
            assert slot in {63, 64}

    def slots(genesis_time: int) -> Iterator[Tuple[(int, int)]]:
        assert genesis_time == 0
        yield 63, 1664
        yield 64, 1676

    def get_our_pubkeys(watched_keys: List[WatchedKeyConfig], web3signer: Web3Signer) -> set[str]:
        assert watched_keys == [WatchedKeyConfig(public_key="0xfff")]
        assert isinstance(web3signer, Web3Signer)

        return {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee", "0xfff"}

    def process_missed_attestations(
        beacon: Beacon,
        beacon_type: BeaconType,
        epoch_to_index_to_validator_index: LimitedDict,
        epoch: int,
    ) -> set[int]:
        assert isinstance(beacon, Beacon)
        assert beacon_type is BeaconType.OLD_TEKU
        assert epoch_to_index_to_validator_index[1] == {
            0: Validator(pubkey="0xaaa", effective_balance=32000000000, slashed=False),
            2: Validator(pubkey="0xccc", effective_balance=32000000000, slashed=False),
            4: Validator(pubkey="0xeee", effective_balance=32000000000, slashed=False),
        }
        assert epoch == 1

        return {0, 4}

    def process_double_missed_attestations(
        indexes_that_missed_attestation: set[int],
        indexes_that_previously_missed_attestation: set[int],
        epoch_to_index_to_validator_index: LimitedDict,
        epoch: int,
        slack: Slack,
    ) -> set[int]:
        assert indexes_that_missed_attestation == {0, 4}
        assert indexes_that_previously_missed_attestation == set()
        assert epoch_to_index_to_validator_index[1] == {
            0: Validator(pubkey="0xaaa", effective_balance=32000000000, slashed=False),
            2: Validator(pubkey="0xccc", effective_balance=32000000000, slashed=False),
            4: Validator(pubkey="0xeee", effective_balance=32000000000, slashed=False),
        }
        assert epoch == 1
        assert isinstance(slack, Slack)

        return {4}

    def process_future_blocks_proposal(
        beacon: Beacon, pubkeys: set[str], slot: int, is_new_epoch: bool
    ) -> int:
        assert isinstance(beacon, Beacon)
        assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee", "0xfff"}
        assert slot in {63, 64}
        assert is_new_epoch is True

        return 1

    def process_missed_blocks_finalized(
        beacon: Beacon,
        last_processed_finalized_slot: int,
        slot: int,
        pubkeys: set[str],
        slack: Slack,
    ) -> int:
        assert isinstance(beacon, Beacon)
        assert last_processed_finalized_slot == 63
        assert slot in {63, 64}
        assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee", "0xfff"}
        assert isinstance(slack, Slack)

        return 63

    def process_suboptimal_attestations(
        beacon: Beacon,
        potential_block: str | None,
        slot: int,
        index_to_validator: dict[int, Validator],
    ) -> set[int]:
        assert isinstance(beacon, Beacon)
        assert potential_block == "A BLOCK"
        assert slot in {63, 64}
        assert index_to_validator == {
            0: Validator(pubkey="0xaaa", effective_balance=32000000000, slashed=False),
            2: Validator(pubkey="0xccc", effective_balance=32000000000, slashed=False),
            4: Validator(pubkey="0xeee", effective_balance=32000000000, slashed=False),
        }

        return {0}

    def process_missed_blocks(
        beacon: Beacon,
        potential_block: str | None,
        slot: int,
        pubkeys: set[str],
        slack: Slack,
    ) -> bool:
        assert isinstance(beacon, Beacon)
        assert potential_block == "A BLOCK"
        assert slot in {63, 64}
        assert pubkeys == {"0xaaa", "0xbbb", "0xccc", "0xddd", "0xeee", "0xfff"}
        assert isinstance(slack, Slack)

        return True

    def process_rewards(
        beacon: Beacon,
        beacon_type: BeaconType,
        epoch: int,
        net_epoch2active_idx2val: dict[int, Validator],
        our_epoch2active_idx2val: dict[int, Validator],
    ) -> None:
        assert isinstance(beacon, Beacon)
        assert isinstance(beacon_type, BeaconType)
        assert epoch == 1
        assert net_epoch2active_idx2val[1] == {
            0: Validator(pubkey="0xaaa", effective_balance=32000000000, slashed=False),
            2: Validator(pubkey="0xccc", effective_balance=32000000000, slashed=False),
            4: Validator(pubkey="0xeee", effective_balance=32000000000, slashed=False),
        }

    def write_liveness_file(liveness_file: Path) -> None:
        assert liveness_file == Path("/path/to/liveness")

    entrypoint.Beacon = Beacon  # type: ignore
    entrypoint.Coinbase = Coinbase  # type: ignore
    entrypoint.Web3Signer = Web3Signer  # type: ignore
    entrypoint.Relays = Relays  # type: ignore
    entrypoint.get_our_pubkeys = get_our_pubkeys  # type: ignore
    entrypoint.process_missed_attestations = process_missed_attestations  # type: ignore

    entrypoint.process_double_missed_attestations = (
        process_double_missed_attestations  # type:ignore
    )

    entrypoint.slots = slots  # type: ignore
    entrypoint.process_future_blocks_proposal = process_future_blocks_proposal  # type: ignore
    entrypoint.process_missed_blocks_finalized = process_missed_blocks_finalized  # type: ignore
    entrypoint.process_suboptimal_attestations = process_suboptimal_attestations  # type: ignore
    entrypoint.process_missed_blocks_head = process_missed_blocks  # type: ignore
    entrypoint.process_rewards = process_rewards  # type: ignore
    entrypoint.write_liveness_file = write_liveness_file  # type: ignore

    _handler(
        beacon_url="http://localhost:5052",
        execution_url=None,
        watched_keys=[WatchedKeyConfig(public_key="0xfff")],
        web3signer_url="http://localhost:9000",
        default_fee_recipient=None,
        slack_channel="my slack channel",
        slack_token="my_slack_token",
        beacon_type=BeaconType.OLD_TEKU,
        relays_url=["http://my-awesome-relay.com"],
        liveness_file=Path("/path/to/liveness"),
    )

    assert Coinbase.nb_calls == 2


def test_invalid_config() -> None:
    path = Path(assets.__file__).parent / "invalid_config.yaml"

    with raises(BadParameter):
        handler(path)
