from eth_validator_watcher.missed_blocks import handle_missed_block_detection
from eth_validator_watcher.models import DataBlock, ProposerDuties
from prometheus_client import Counter


def test_no_hole_no_block_missed_they_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return False

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("a", "a")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=1,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xddd"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 0.0


def test_no_hole_no_block_missed_we_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return False

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("b", "b")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=1,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xccc"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 0.0


def test_no_hole_block_missed_they_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return True

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("c", "c")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=1,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xddd"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 0.0


def test_no_hole_block_missed_we_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return True

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("d", "d")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=1,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xccc"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 1.0


def test_hole_no_block_missed_they_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return False

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("e", "e")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=0,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xddd"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 0.0


def test_hole_no_block_missed_we_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return False

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("f", "f")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=0,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xbbb"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 1.0


def test_hole_block_missed_they_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return True

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("g", "g")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=0,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xddd"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 0.0


def test_hole_block_missed_they_propose_and_we_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return True

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("h", "h")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=0,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xccc"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 1.0


def test_hole_block_missed_we_propose_and_they_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return True

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("i", "i")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=0,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xaaa", "0xbbb"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 1.0


def test_hole_block_missed_we_propose():
    class Beacon:
        @staticmethod
        def is_block_missed(_: int) -> bool:
            return True

        @staticmethod
        def get_proposer_duties(_: int) -> ProposerDuties:
            return ProposerDuties(
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=0),
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1),
                    ProposerDuties.Data(pubkey="0xccc", validator_index=2, slot=2),
                ]
            )

    counter = Counter("j", "j")

    assert (
        handle_missed_block_detection(
            beacon=Beacon(),
            data_block=DataBlock(slot=2),
            previous_slot=0,
            missed_block_proposals_counter=counter,
            our_pubkeys={"0xbbb", "0xccc"},
        )
        == 2
    )

    assert counter.collect()[0].samples[0].value == 2.0
