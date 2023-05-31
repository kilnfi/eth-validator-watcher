from typing import Optional

from prometheus_client import Counter

from eth_validator_watcher import missed_blocks
from eth_validator_watcher.missed_blocks import (
    missed_block_proposals_count,
    process_missed_blocks,
)
from eth_validator_watcher.models import Block, ProposerDuties


def test_process_missed_blocks_no_block() -> None:
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

    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    counter_before = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore
    process_missed_blocks(Beacon(), None, 3, {"0xaaa", "0xddd"}, slack)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    delta = counter_after - counter_before
    assert delta == 1
    assert slack.counter == 1


def test_process_missed_blocks_habemus_blockam() -> None:
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

    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    counter_before = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore
    process_missed_blocks(Beacon(), "A BLOCK", 3, {"0xaaa", "0xddd"}, slack)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    delta = counter_after - counter_before
    assert delta == 0
    assert slack.counter == 0
