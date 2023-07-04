from eth_validator_watcher.missed_blocks import (
    missed_block_proposals_count,
    missed_block_proposals_count_details,
    process_missed_blocks,
)
from eth_validator_watcher.models import ProposerDuties


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
    assert process_missed_blocks(Beacon(), None, 3, {"0xaaa", "0xddd"}, slack)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    # Has sample for slot
    has_slot_metric = False
    for sample in missed_block_proposals_count_details.collect()[0].samples:
        if sample.labels["slot"] == "3":
            has_slot_metric = True

    delta = counter_after - counter_before
    assert delta == 1
    assert slack.counter == 1
    assert has_slot_metric


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
    assert not process_missed_blocks(Beacon(), "A BLOCK", 2, {"0xaaa", "0xddd"}, slack)  # type: ignore
    counter_after = missed_block_proposals_count.collect()[0].samples[0].value  # type: ignore

    # Has sample for slot
    has_slot_metric = False
    for sample in missed_block_proposals_count_details.collect()[0].samples:
        if sample.labels["slot"] == "2":
            has_slot_metric = True

    delta = counter_after - counter_before
    assert delta == 0
    assert slack.counter == 0
    assert not (has_slot_metric)
