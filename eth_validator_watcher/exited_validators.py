"""Contains the ExitedValidators class, which is responsible for managing the exited
validators."""


from prometheus_client import Gauge

from .models import Validators
from .utils import Slack

metric_our_exited_validators_count = Gauge(
    "our_exited_validators_count",
    "Our exited validators count",
)


class ExitedValidators:
    """Exited validators abstraction."""

    def __init__(self, slack: Slack | None) -> None:
        """Exited validators

        Parameters:
        slack: Optional slack client
        """
        self.__our_exited_unslashed_indexes: set[int] | None = None
        self.__slack = slack

    def process(
        self,
        our_exited_unslashed_index_to_validator: dict[
            int, Validators.DataItem.Validator
        ],
        our_withdrawal_index_to_validator: dict[int, Validators.DataItem.Validator],
    ) -> None:
        """Process exited validators.

        Parameters:
        our_exited_unslashed_index_to_validator: Dictionary with:
            key  : our exited validator index
            value: validator data corresponding to the validator index
        """

        our_exited_unslashed_indexes = set(our_exited_unslashed_index_to_validator)

        our_unslashed_withdrawal_index_to_validator = {
            index
            for index, validator in our_withdrawal_index_to_validator.items()
            if not validator.slashed
        }

        our_exited_indexes = set(our_exited_unslashed_index_to_validator) | set(
            our_unslashed_withdrawal_index_to_validator
        )

        metric_our_exited_validators_count.set(len(our_exited_indexes))

        if self.__our_exited_unslashed_indexes is None:
            self.__our_exited_unslashed_indexes = our_exited_unslashed_indexes
            return

        our_new_exited_unslashed_indexes = (
            our_exited_unslashed_indexes - self.__our_exited_unslashed_indexes
        )

        for index in our_new_exited_unslashed_indexes:
            message = f"🚶 Our validator {our_exited_unslashed_index_to_validator[index].pubkey[:10]} is exited"
            print(message)

            if self.__slack is not None:
                self.__slack.send_message(message)

        self.__our_exited_unslashed_indexes = our_exited_unslashed_indexes
