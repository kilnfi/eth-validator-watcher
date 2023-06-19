from typing import Optional

from prometheus_client import Gauge

from .utils import Slack

our_exited_slashed_validators_count = Gauge(
    "our_exited_slashed_validators_count",
    "Our exited slashed validators count",
)

total_exited_slashed_validators_count = Gauge(
    "total_exited_slashed_validators_count",
    "Total exited slashed validators count",
)


class SlashedValidators:
    def __init__(self, slack: Optional[Slack]) -> None:
        self.__total_exited_slashed_indexes: Optional[set[int]] = None
        self.__our_exited_slashed_indexes: Optional[set[int]] = None
        self.__slack = slack

    def process(
        self,
        total_exited_slashed_index_to_pubkey: dict[int, str],
        our_exited_slashed_index_to_pubkey: dict[int, str],
    ) -> None:
        total_exited_slashed_indexes = set(total_exited_slashed_index_to_pubkey)
        our_exited_slashed_indexes = set(our_exited_slashed_index_to_pubkey)

        total_exited_slashed_validators_count.set(len(total_exited_slashed_indexes))
        our_exited_slashed_validators_count.set(len(our_exited_slashed_indexes))

        if (
            self.__total_exited_slashed_indexes is None
            or self.__our_exited_slashed_indexes is None
        ):
            self.__total_exited_slashed_indexes = total_exited_slashed_indexes
            self.__our_exited_slashed_indexes = our_exited_slashed_indexes
            return

        total_new_exited_slashed_indexes = (
            total_exited_slashed_indexes - self.__total_exited_slashed_indexes
        )

        our_new_exited_slashed_indexes = (
            our_exited_slashed_indexes - self.__our_exited_slashed_indexes
        )

        not_our_new_exited_slashed_indexes = (
            total_new_exited_slashed_indexes - our_new_exited_slashed_indexes
        )

        for index in not_our_new_exited_slashed_indexes:
            print(
                f"✂️      validator {total_exited_slashed_index_to_pubkey[index][:10]} is slashed"
            )

        for index in our_new_exited_slashed_indexes:
            message = f"🔕 Our validator {our_exited_slashed_index_to_pubkey[index][:10]} is slashed"
            print(message)

            if self.__slack is not None:
                self.__slack.send_message(message)

        self.__total_exited_slashed_indexes = total_exited_slashed_indexes
        self.__our_exited_slashed_indexes = our_exited_slashed_indexes
