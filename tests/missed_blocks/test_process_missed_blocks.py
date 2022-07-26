from typing import Optional

from prometheus_client import Counter
from eth_validator_watcher.missed_blocks import (
    process_missed_blocks,
    missed_block_proposals_count,
)
from eth_validator_watcher.models import Block, ProposerDuties
from eth_validator_watcher import missed_blocks


def test_process_missed_blocks_previous_slot_none() -> None:
    class Beacon:
        @staticmethod
        def get_proposer_duties(epoch: int) -> ProposerDuties:
            assert epoch == 0

            return ProposerDuties(
                dependent_root="0xfff",
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ],
            )

    counter_before = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore
    process_missed_blocks(Beacon(), None, 1, None, set(), None)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    delta = counter_after - counter_before
    assert delta == 0


def test_process_missed_blocks_previous_slot_far_away() -> None:
    class Beacon:
        @staticmethod
        def get_proposer_duties(epoch: int) -> ProposerDuties:
            assert epoch == 0

            return ProposerDuties(
                dependent_root="0xfff",
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                    ProposerDuties.Data(pubkey="0xddd", validator_index=3, slot=3),
                ],
            )

        @staticmethod
        def get_potential_block(slot: int) -> Optional[Block]:
            if slot == 1:
                return "something_that_is_not_none"  # type: ignore
            elif slot == 2:
                return None

            assert False, "We should not be here"

    counter_before = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore
    process_missed_blocks(Beacon(), "something_that_is_not_none", 3, 0, {"0xbbb", "0xccc"}, None)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    delta = counter_after - counter_before
    assert delta == 1


def test_process_missed_blocks_previous_slot_far_away_2() -> None:
    class Beacon:
        @staticmethod
        def get_proposer_duties(epoch: int) -> ProposerDuties:
            assert epoch == 0

            return ProposerDuties(
                dependent_root="0xfff",
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                    ProposerDuties.Data(pubkey="0xddd", validator_index=3, slot=3),
                ],
            )

        @staticmethod
        def get_potential_block(slot: int) -> Optional[Block]:
            if slot == 1:
                return None  # type: ignore
            elif slot == 2:
                return None

            assert False, "We should not be here"

    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    counter_before = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore
    process_missed_blocks(Beacon(), None, 3, 0, {"0xaaa", "0xddd"}, slack)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    delta = counter_after - counter_before
    assert delta == 1
    assert slack.counter == 1
