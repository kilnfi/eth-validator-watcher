from eth_validator_watcher.models import ProposerDuties
from eth_validator_watcher.next_blocks_proposal import process_future_blocks_proposal


class Beacon:
    @staticmethod
    def get_proposer_duties(epoch: int) -> ProposerDuties:
        return {
            42: ProposerDuties(
                dependent_root="0xfff",
                data=[
                    ProposerDuties.Data(pubkey="0xaaa", validator_index=0, slot=1344)
                ],
            ),
            43: ProposerDuties(
                dependent_root="0xfff",
                data=[
                    ProposerDuties.Data(pubkey="0xbbb", validator_index=1, slot=1376)
                ],
            ),
        }[epoch]


def test_handle_next_blocks_proposal_no_work():
    assert (
        process_future_blocks_proposal(Beacon(), set(), 1344, False) == 0  # type: ignore
    )


def test_handle_next_blocks_proposal_work():
    assert (
        process_future_blocks_proposal(Beacon(), {"0xaaa"}, 1344, True)  # type: ignore
        == 1
    )
