"""Contains the logic to compute the duration of the entry queue."""

from prometheus_client import Gauge

MIN_PER_EPOCH_CHURN_LIMIT = 4
MAX_PER_EPOCH_CHURN_LIMIT = 8
CHURN_LIMIT_QUOTIENT = 65536
NB_SECONDS_PER_SLOT = 12
NB_SLOT_PER_EPOCH = 32
NB_SECONDS_PER_EPOCH = NB_SECONDS_PER_SLOT * NB_SLOT_PER_EPOCH

# TODO: Compute this dynamically
BUCKETS: list[tuple[int, int]] = [
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
    (1_376_256, 21),
    (1_441_792, 22),
    (1_507_328, 23),
    (1_572_864, 24),
    (1_638_400, 25),
    (1_703_936, 26),
    (1_769_472, 27),
    (1_835_008, 28),
    (1_900_544, 29),
    (1_966_080, 30),
    (2_031_616, 31),
    (2_097_152, 32),
    (2_162_688, 33),
    (2_228_224, 34),
    (2_293_760, 35),
    (2_359_296, 36),
    (2_424_832, 37),
    (2_490_368, 38),
    (2_555_904, 39),
    (2_621_440, 40),
]

metric_entry_queue_duration_sec = Gauge(
    "entry_queue_duration_sec",
    "Entry queue duration in seconds",
)


def compute_validators_churn(nb_active_validators: int) -> int:
    """Compute the number of validators that can exit the entry queue per epoch.

    Parameters:
    nb_active_validators: The number of currently active validators
    """
    return min(MAX_PER_EPOCH_CHURN_LIMIT, max(MIN_PER_EPOCH_CHURN_LIMIT, nb_active_validators // CHURN_LIMIT_QUOTIENT))


def get_bucket_index(validator_index: int) -> int:
    """Get the bucket index of a validator.

    Parameters:
    validator_index: The index of the validator
    """
    for index, (bucket_start, _) in enumerate(BUCKETS):
        if validator_index < bucket_start:
            return index - 1

    raise RuntimeError("Validator index is too high")


def compute_duration_sec(
    nb_active_validators: int, position_in_entry_queue: int
) -> int:
    """Compute the remaining time before a validator is active if no validator wants to
    exit.

    Parameters:
    nb_active_validators   : The number of currently active validators
    position_in_entry_queue: The position of the validator in the entry queue
    """
    start_bucket_index = get_bucket_index(nb_active_validators)
    stop_bucket_index = get_bucket_index(nb_active_validators + position_in_entry_queue)

    if start_bucket_index == stop_bucket_index:
        return (
            position_in_entry_queue // compute_validators_churn(nb_active_validators)
        ) * NB_SECONDS_PER_EPOCH
    # Compute the number of validators in the first bucket
    start_limit, _ = BUCKETS[start_bucket_index + 1]
    number_validators_in_start_bucket = start_limit - nb_active_validators

    # Compute the number of validators in the stop bucket
    stop_limit, _ = BUCKETS[stop_bucket_index]

    number_validators_in_stop_bucket = (
        nb_active_validators + position_in_entry_queue + 1 - stop_limit
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
    nb_active_validators   : The number of currently active validators
    position_in_entry_queue: The position of the validator in the entry queue
    """

    duration_sec = compute_duration_sec(nb_active_validators, position_in_entry_queue)
    metric_entry_queue_duration_sec.set(duration_sec)
