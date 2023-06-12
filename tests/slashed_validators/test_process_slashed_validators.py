from eth_validator_watcher.slashed_validators import (
    SlashedValidators,
    our_exited_slashed_validators_count,
    total_exited_slashed_validators_count,
)


def test_process_slashed_validators():
    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    total_exited_slashed_index_to_pubkey = {42: "0x1234", 43: "0x5678"}
    our_exited_slashed_index_to_pubkey = {44: "0x9012", 45: "0x3456"}

    slashed_validators = SlashedValidators(slack)  # type: ignore

    total_exited_slashed_index_to_pubkey = {
        42: "0x1234",
        43: "0x5678",
        44: "0x9012",
        45: "0x3456",
        46: "0xabcd",
    }

    our_exited_slashed_index_to_pubkey = {
        44: "0x9012",
        45: "0x3456",
    }

    slashed_validators.process(
        total_exited_slashed_index_to_pubkey, our_exited_slashed_index_to_pubkey
    )

    assert total_exited_slashed_validators_count.collect()[0].samples[0].value == 5  # type: ignore
    assert our_exited_slashed_validators_count.collect()[0].samples[0].value == 2  # type: ignore
    assert slack.counter == 0

    assert (
        slashed_validators._SlashedValidators__total_exited_slashed_indexes  # type: ignore
        == {
            42,
            43,
            44,
            45,
            46,
        }
    )

    assert (
        slashed_validators._SlashedValidators__our_exited_slashed_indexes  # type: ignore
        == {44, 45}
    )

    total_exited_slashed_index_to_pubkey = {
        42: "0x1234",
        43: "0x5678",
        44: "0x9012",
        45: "0x3456",
        46: "0xabcd",
        47: "0xefgh",
    }

    our_exited_slashed_index_to_pubkey = {44: "0x9012", 45: "0x3456", 48: "0x5432"}

    slashed_validators.process(
        total_exited_slashed_index_to_pubkey, our_exited_slashed_index_to_pubkey
    )

    assert total_exited_slashed_validators_count.collect()[0].samples[0].value == 6  # type: ignore
    assert our_exited_slashed_validators_count.collect()[0].samples[0].value == 3  # type: ignore
    assert slack.counter == 1

    assert (
        slashed_validators._SlashedValidators__total_exited_slashed_indexes  # type: ignore
        == {
            42,
            43,
            44,
            45,
            46,
            47,
        }
    )

    assert (
        slashed_validators._SlashedValidators__our_exited_slashed_indexes  # type: ignore
        == {44, 45, 48}
    )
