"""Contains the SlashedValidators class, which is responsible for managing the slashed
validators."""
from prometheus_client import Gauge

from .models import Validators
from .utils import Slack

metric_our_slashed_validators_count = Gauge(
    "our_slashed_validators_count",
    "Our slashed validators count",
)

metric_total_slashed_validators_count = Gauge(
    "total_slashed_validators_count",
    "Total slashed validators count",
)


class SlashedValidators:
    """Slashed validators abstraction."""

    def __init__(self, slack: Slack | None) -> None:
        """Slashed validators

        Parameters:
        slack: Optional slack client
        """
        self.__total_exited_slashed_indexes: set[int] | None = None
        self.__our_exited_slashed_indexes: set[int] | None = None
        self.__slack = slack

    def process(
        self,
        total_exited_slashed_index_to_validator: dict[
            int, Validators.DataItem.Validator
        ],
        our_exited_slashed_index_to_validator: dict[int, Validators.DataItem.Validator],
        total_withdrawal_index_to_validator: dict[int, Validators.DataItem.Validator],
        our_withdrawal_index_to_validator: dict[int, Validators.DataItem.Validator],
    ) -> None:
        """Process slashed validators.

        Parameters:
        total_exited_slashed_index_to_validator: Dictionary with:
            key  : total exited validator index
            value: validator data corresponding to the validator index
        our_exited_slashed_index_to_validator  : Dictionary with:
            key  : our exited validator index
            value: validator data corresponding to the validator index
        total_withdrawal_index_to_validator    : Dictionary with:
            key  : total withdrawal validator index
            value: validator data corresponding to the validator index
        our_withdrawal_index_to_validator      : Dictionary with:
            key  : our withdrawal validator index
            value: validator data corresponding to the validator index
        """
        total_slashed_withdrawal_index_to_validator = {
            index
            for index, validator in total_withdrawal_index_to_validator.items()
            if validator.slashed
        }

        our_slashed_withdrawal_index_to_validator = {
            index
            for index, validator in our_withdrawal_index_to_validator.items()
            if validator.slashed
        }

        total_slashed_indexes = set(total_exited_slashed_index_to_validator) | set(
            total_slashed_withdrawal_index_to_validator
        )

        our_slashed_indexes = set(our_exited_slashed_index_to_validator) | set(
            our_slashed_withdrawal_index_to_validator
        )

        metric_total_slashed_validators_count.set(len(total_slashed_indexes))
        metric_our_slashed_validators_count.set(len(our_slashed_indexes))

        total_exited_slashed_indexes = set(total_exited_slashed_index_to_validator)
        our_exited_slashed_indexes = set(our_exited_slashed_index_to_validator)

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
                f"🔪     validator {total_exited_slashed_index_to_validator[index].pubkey[:10]} is slashed"
            )

        for index in our_new_exited_slashed_indexes:
            message = f"🔕 Our validator {our_exited_slashed_index_to_validator[index].pubkey[:10]} is slashed"
            print(message)

            if self.__slack is not None:
                self.__slack.send_message(message)

        self.__total_exited_slashed_indexes = total_exited_slashed_indexes
        self.__our_exited_slashed_indexes = our_exited_slashed_indexes
