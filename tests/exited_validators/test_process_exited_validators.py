from eth_validator_watcher.exited_validators import (
    ExitedValidators,
    our_exited_unslashed_validators_count,
)


def test_process_exited_validators():
    class Slack:
        def __init__(self):
            self.counter = 0

        def send_message(self, _: str) -> None:
            self.counter += 1

    slack = Slack()

    our_exited_unslashed_index_to_pubkey = {44: "0x9012", 45: "0x3456"}

    exited_validators = ExitedValidators(slack)  # type: ignore

    our_exited_unslashed_index_to_pubkey = {
        44: "0x9012",
        45: "0x3456",
    }

    exited_validators.process(our_exited_unslashed_index_to_pubkey)

    assert our_exited_unslashed_validators_count.collect()[0].samples[0].value == 2  # type: ignore
    assert slack.counter == 0

    assert (
        exited_validators._ExitedValidators__our_exited_unslashed_indexes  # type: ignore
        == {44, 45}
    )

    our_exited_unslashed_index_to_pubkey = {44: "0x9012", 45: "0x3456", 48: "0x5432"}
    exited_validators.process(our_exited_unslashed_index_to_pubkey)

    assert our_exited_unslashed_validators_count.collect()[0].samples[0].value == 3  # type: ignore
    assert slack.counter == 1

    assert (
        exited_validators._ExitedValidators__our_exited_unslashed_indexes  # type: ignore
        == {44, 45, 48}
    )
