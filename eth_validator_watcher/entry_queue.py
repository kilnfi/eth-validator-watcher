"""Contains the logic to compute the duration of the entry queue."""

from prometheus_client import Gauge

MIN_PER_EPOCH_CHURN_LIMIT = 4
CHURN_LIMIT_QUOTIENT = 65536
NB_SECONDS_PER_SLOT = 12
NB_SLOT_PER_EPOCH = 32
NB_SECONDS_PER_EPOCH = NB_SECONDS_PER_SLOT * NB_SLOT_PER_EPOCH

# TODO: Compute this dynamically
BUCKETS = [
    (0, 4),
    (327_680, 5),
    (393_216, 6),
    (458_752, 7),
    (524_288, 8),
    (589_824, 9),
    (655_360, 10),
    (720_896, 11),
    (786_432, 12),
    (851_968, 13),
    (917_504, 14),
    (983_040, 15),
    (1_048_576, 16),
    (1_114_112, 17),
    (1_179_648, 18),
    (1_245_184, 19),
    (1_310_720, 20),
]

entry_queue_duration_sec = Gauge(
    "entry_queue_duration_sec",
    "Entry queue duration in seconds",
)


def compute_validators_churn(nb_active_validators: int) -> int:
    """Compute the number of validators that can exit the entry queue per epoch.

    Parameters:
    nb_active_validators: The number of currently active validators
    """
    return max(MIN_PER_EPOCH_CHURN_LIMIT, nb_active_validators // CHURN_LIMIT_QUOTIENT)


def compute_pessimistic_duration_sec(
    nb_active_validators: int, position_in_entry_queue: int
) -> int:
    """Compute a pessimistic estimation of when a validator will exit the entry queue.

    Parameters:
    nb_active_validators: The number of currently active validators
    position_in_entry_queue: The position of the validator in the entry queue
    """
    return (
        position_in_entry_queue // compute_validators_churn(nb_active_validators)
    ) * NB_SECONDS_PER_EPOCH


def get_bucket_index(validator_index: int) -> int:
    """Get the bucket index of a validator.

    Parameters:
    validator_index: The index of the validator
    """
    for index, (bucket_start, _) in enumerate(BUCKETS):
        if validator_index < bucket_start:
            return index - 1

    raise RuntimeError("Validator index is too high")


def compute_optimistic_duration_sec(
    nb_active_validators: int, position_in_entry_queue: int
) -> int:
    """Compute an optimistic estimation of when a validator will exit the entry queue.

    Parameters:
    nb_active_validators: The number of currently active validators
    position_in_entry_queue: The position of the validator in the entry queue
    """
    start_bucket_index = get_bucket_index(nb_active_validators)
    stop_bucket_index = get_bucket_index(nb_active_validators + position_in_entry_queue)

    if start_bucket_index == stop_bucket_index:
        return compute_pessimistic_duration_sec(
            nb_active_validators, position_in_entry_queue
        )

    # Compute the number of validators in the first bucket
    start_limit, _ = BUCKETS[start_bucket_index + 1]
    number_validators_in_start_bucket = start_limit - nb_active_validators

    # Compute the number of validators in the stop bucket
    stop_limit, _ = BUCKETS[stop_bucket_index]

    number_validators_in_stop_bucket = (
        nb_active_validators + position_in_entry_queue - stop_limit + 1
    )

    def fill_bucket(index: int) -> int:
        if index < start_bucket_index or index > stop_bucket_index:
            return 0
        if index == start_bucket_index:
            return number_validators_in_start_bucket
        elif index == stop_bucket_index:
            return number_validators_in_stop_bucket
        else:
            begin, _ = BUCKETS[index]
            end, _ = BUCKETS[index + 1]
            return end - begin

    numbers_of_validators = [fill_bucket(index) for index in range(len(BUCKETS))]

    nb_of_needed_epochs = sum(
        (number_of_validators // churn)
        for (_, churn), number_of_validators in zip(BUCKETS, numbers_of_validators)
    )

    return nb_of_needed_epochs * NB_SECONDS_PER_EPOCH


def export_duration_sec(
    nb_active_validators: int, position_in_entry_queue: int
) -> None:
    """Export the duration of the entry queue.

    This function does the average of the pessimistic and optimistic duration
    estimations.

    Parameters:
    nb_active_validators: The number of currently active validators
    position_in_entry_queue: The position of the validator in the entry queue
    """
    result = (
        compute_optimistic_duration_sec(nb_active_validators, position_in_entry_queue)
        + compute_pessimistic_duration_sec(
            nb_active_validators, position_in_entry_queue
        )
    ) // 2

    entry_queue_duration_sec.set(result)
