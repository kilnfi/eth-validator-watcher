from math import e
from typing import Union

import pytest

from eth_validator_watcher.beacon import NoBlockError
from eth_validator_watcher.missed_blocks import (
    metric_missed_block_proposals_finalized_count,
    process_missed_blocks_finalized,
)
from eth_validator_watcher.models import BlockIdentierType, Header, ProposerDuties


def test_process_missed_blocks_finalized_future_slot() -> None:
    with pytest.raises(AssertionError):
        process_missed_blocks_finalized("a beacon", 42, 41, {}, None)  # type: ignore


def test_process_missed_blocks_finalized_nominal() -> None:
    Data = ProposerDuties.Data

    class Slack:
        def __init__(self) -> None:
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    class Beacon:
        @staticmethod
        def get_header(block_identifier: Union[BlockIdentierType, int]) -> Header:
            def header(slot: int) -> Header:
                return Header(
                    data=Header.Data(
                        header=Header.Data.Header(
                            message=Header.Data.Header.Message(slot=slot)
                        )
                    )
                )

            block_identifier_to_header = {
                43: header(43),
                57: header(57),
                58: header(58),
                91: header(91),
                99: header(99),
                100: header(100),
                BlockIdentierType.FINALIZED: header(100),
            }

            try:
                return block_identifier_to_header[block_identifier]
            except KeyError:
                raise NoBlockError

        @staticmethod
        def get_proposer_duties(epoch: int) -> ProposerDuties:
            epoch_to_duties = {
                1: ProposerDuties(
                    dependent_root="0xfff",
                    data=[
                        Data(pubkey="0x00", validator_index=32, slot=32),
                        Data(pubkey="0x01", validator_index=33, slot=33),
                        Data(pubkey="0x02", validator_index=34, slot=34),
                        Data(pubkey="0x03", validator_index=35, slot=35),
                        Data(pubkey="0x04", validator_index=36, slot=36),
                        Data(pubkey="0x05", validator_index=37, slot=37),
                        Data(pubkey="0x06", validator_index=38, slot=38),
                        Data(pubkey="0x07", validator_index=39, slot=39),
                        Data(pubkey="0x08", validator_index=40, slot=40),
                        Data(pubkey="0x09", validator_index=41, slot=41),
                        Data(pubkey="0x10", validator_index=42, slot=42),
                        Data(pubkey="0x11", validator_index=43, slot=43),
                        Data(pubkey="0x12", validator_index=44, slot=44),
                        Data(pubkey="0x13", validator_index=45, slot=45),
                        Data(pubkey="0x14", validator_index=46, slot=46),
                        Data(pubkey="0x15", validator_index=47, slot=47),
                        Data(pubkey="0x16", validator_index=48, slot=48),
                        Data(pubkey="0x17", validator_index=49, slot=49),
                        Data(pubkey="0x18", validator_index=50, slot=50),
                        Data(pubkey="0x19", validator_index=51, slot=51),
                        Data(pubkey="0x20", validator_index=52, slot=52),
                        Data(pubkey="0x21", validator_index=53, slot=53),
                        Data(pubkey="0x22", validator_index=54, slot=54),
                        Data(pubkey="0x23", validator_index=55, slot=55),
                        Data(pubkey="0x24", validator_index=56, slot=56),
                        Data(pubkey="0x25", validator_index=57, slot=57),
                        Data(pubkey="0x26", validator_index=58, slot=58),
                        Data(pubkey="0x27", validator_index=59, slot=59),
                        Data(pubkey="0x28", validator_index=60, slot=60),
                        Data(pubkey="0x29", validator_index=61, slot=61),
                        Data(pubkey="0x30", validator_index=62, slot=62),
                        Data(pubkey="0x31", validator_index=63, slot=63),
                    ],
                ),
                2: ProposerDuties(
                    dependent_root="0xfff",
                    data=[
                        Data(pubkey="0x32", validator_index=64, slot=64),
                        Data(pubkey="0x33", validator_index=65, slot=65),
                        Data(pubkey="0x34", validator_index=66, slot=66),
                        Data(pubkey="0x35", validator_index=67, slot=67),
                        Data(pubkey="0x36", validator_index=68, slot=68),
                        Data(pubkey="0x37", validator_index=69, slot=69),
                        Data(pubkey="0x38", validator_index=70, slot=70),
                        Data(pubkey="0x39", validator_index=71, slot=71),
                        Data(pubkey="0x40", validator_index=72, slot=72),
                        Data(pubkey="0x41", validator_index=73, slot=73),
                        Data(pubkey="0x42", validator_index=74, slot=74),
                        Data(pubkey="0x43", validator_index=75, slot=75),
                        Data(pubkey="0x44", validator_index=76, slot=76),
                        Data(pubkey="0x45", validator_index=77, slot=77),
                        Data(pubkey="0x46", validator_index=78, slot=78),
                        Data(pubkey="0x47", validator_index=79, slot=79),
                        Data(pubkey="0x48", validator_index=80, slot=80),
                        Data(pubkey="0x49", validator_index=81, slot=81),
                        Data(pubkey="0x50", validator_index=82, slot=82),
                        Data(pubkey="0x51", validator_index=83, slot=83),
                        Data(pubkey="0x52", validator_index=84, slot=84),
                        Data(pubkey="0x53", validator_index=85, slot=85),
                        Data(pubkey="0x54", validator_index=86, slot=86),
                        Data(pubkey="0x55", validator_index=87, slot=87),
                        Data(pubkey="0x56", validator_index=88, slot=88),
                        Data(pubkey="0x57", validator_index=89, slot=89),
                        Data(pubkey="0x58", validator_index=90, slot=90),
                        Data(pubkey="0x59", validator_index=91, slot=91),
                        Data(pubkey="0x60", validator_index=92, slot=92),
                        Data(pubkey="0x61", validator_index=93, slot=93),
                        Data(pubkey="0x62", validator_index=94, slot=94),
                        Data(pubkey="0x63", validator_index=95, slot=95),
                    ],
                ),
                3: ProposerDuties(
                    dependent_root="0xfff",
                    data=[
                        Data(pubkey="0x64", validator_index=96, slot=96),
                        Data(pubkey="0x65", validator_index=97, slot=97),
                        Data(pubkey="0x66", validator_index=98, slot=98),
                        Data(pubkey="0x67", validator_index=99, slot=99),
                        Data(pubkey="0x68", validator_index=100, slot=100),
                        Data(pubkey="0x69", validator_index=101, slot=101),
                        Data(pubkey="0x70", validator_index=102, slot=102),
                        Data(pubkey="0x71", validator_index=103, slot=103),
                        Data(pubkey="0x72", validator_index=104, slot=104),
                        Data(pubkey="0x73", validator_index=105, slot=105),
                        Data(pubkey="0x74", validator_index=106, slot=106),
                        Data(pubkey="0x75", validator_index=107, slot=107),
                        Data(pubkey="0x76", validator_index=108, slot=108),
                        Data(pubkey="0x77", validator_index=109, slot=109),
                        Data(pubkey="0x78", validator_index=110, slot=110),
                        Data(pubkey="0x79", validator_index=111, slot=111),
                        Data(pubkey="0x80", validator_index=112, slot=112),
                        Data(pubkey="0x81", validator_index=113, slot=113),
                        Data(pubkey="0x82", validator_index=114, slot=114),
                        Data(pubkey="0x83", validator_index=115, slot=115),
                        Data(pubkey="0x84", validator_index=116, slot=116),
                        Data(pubkey="0x85", validator_index=117, slot=117),
                        Data(pubkey="0x86", validator_index=118, slot=118),
                        Data(pubkey="0x87", validator_index=119, slot=119),
                        Data(pubkey="0x88", validator_index=120, slot=120),
                        Data(pubkey="0x89", validator_index=121, slot=121),
                        Data(pubkey="0x90", validator_index=122, slot=122),
                        Data(pubkey="0x91", validator_index=123, slot=123),
                        Data(pubkey="0x92", validator_index=124, slot=124),
                        Data(pubkey="0x93", validator_index=125, slot=125),
                        Data(pubkey="0x94", validator_index=126, slot=126),
                        Data(pubkey="0x95", validator_index=127, slot=127),
                    ],
                ),
            }

            return epoch_to_duties[epoch]

    beacon = Beacon()
    slack = Slack()

    counter_before = metric_missed_block_proposals_finalized_count.collect()[0].samples[0].value  # type: ignore

    assert (
        process_missed_blocks_finalized(
            beacon,  # type: ignore
            42,
            150,
            {
                "0x10",  # too soon - slot: 42
                "0x11",  # proposed - slot: 43
                "0x12",  # missed   - slot: 44
                "0x25",  # proposed - slot: 57
                "0x26",  # proposed - slot: 58
                "0x59",  # proposed - slot: 91
                "0x66",  # missed   - slot: 98
                "0x67",  # proposed - slot: 99
                "0x68",  # proposed - slot: 100
                "0x69",  # too late - slot: 101
            },
            slack,  # type: ignore
        )
        == 100
    )

    counter_after = metric_missed_block_proposals_finalized_count.collect()[0].samples[0].value  # type: ignore
    delta = counter_after - counter_before
    assert delta == 2
    assert slack.counter == 2
