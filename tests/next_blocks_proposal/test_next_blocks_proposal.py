from eth_validator_watcher.models import DataBlock, ProposerDuties
from eth_validator_watcher.next_blocks_proposal import handle_next_blocks_proposal


class Beacon:
    @staticmethod
    def get_proposer_duties(epoch: int) -> ProposerDuties:
        return {
            42: ProposerDuties(
                data=[ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=1344)]
            ),
            43: ProposerDuties(
                data=[ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1376)]
            ),
        }[epoch]


def test_handle_next_blocks_proposal_no_work():
    assert handle_next_blocks_proposal(Beacon(), set(), DataBlock(slot=1344), 41) == 42


def test_handle_next_blocks_proposal_work():
    assert (
        handle_next_blocks_proposal(Beacon(), {"0xaaa"}, DataBlock(slot=1344), 41) == 42
    )
