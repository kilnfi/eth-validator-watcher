from typing import Set
import functools
from typing import Optional

from prometheus_client import Gauge

from .utils import Slack

from .beacon import Beacon


print = functools.partial(print, flush=True)

missed_attestations_count = Gauge(
    "missed_attestations_count",
    "Missed attestations count",
)

double_missed_attestations_count = Gauge(
    "double_missed_attestations_count",
    "Double missed attestations count",
)


def process_missed_attestations(
    beacon: Beacon,
    our_active_index_to_pubkey: dict[int, str],
    epoch: int,
) -> set[int]:
    validators_index = set(our_active_index_to_pubkey)
    validators_liveness = beacon.get_validators_liveness(epoch - 1, validators_index)

    dead_indexes = {
        index for index, liveness in validators_liveness.items() if not liveness
    }

    missed_attestations_count.set(len(dead_indexes))

    if len(dead_indexes) == 0:
        return set()

    first_indexes = list(dead_indexes)[:5]

    first_pubkeys = (
        our_active_index_to_pubkey[first_index] for first_index in first_indexes
    )

    short_first_pubkeys = [pubkey[:10] for pubkey in first_pubkeys]
    short_first_pubkeys_str = ", ".join(short_first_pubkeys)

    print(
        f"☹️ Our validator {short_first_pubkeys_str} and "
        f"{len(dead_indexes) - len(short_first_pubkeys)} more "
        f"missed attestation at epoch {epoch - 1}"
    )

    return dead_indexes


def process_double_missed_attestations(
    dead_indexes: set[int],
    previous_dead_indexes: set[int],
    our_active_index_to_pubkey: dict[int, str],
    epoch: int,
    slack: Optional[Slack],
) -> Set[int]:
    double_dead_indexes = dead_indexes & previous_dead_indexes

    double_missed_attestations_count.set(len(double_dead_indexes))

    if len(double_dead_indexes) == 0:
        return set()

    first_indexes = list(double_dead_indexes)[:5]

    first_pubkeys = (
        our_active_index_to_pubkey[first_index] for first_index in first_indexes
    )

    short_first_pubkeys = [pubkey[:10] for pubkey in first_pubkeys]
    short_first_pubkeys_str = ", ".join(short_first_pubkeys)

    message_console = (
        f"😱  Our validator {short_first_pubkeys_str} and "
        f"{len(double_dead_indexes) - len(short_first_pubkeys)} more "
        f"missed 2 attestations in a raw from epoch {epoch - 2}"
    )

    print(message_console)

    if slack is not None:
        message_slack = (
            f"😱  Our validator `{short_first_pubkeys_str}` and "
            f"`{len(double_dead_indexes) - len(short_first_pubkeys)}` more "
            f"missed 2 attestations in a raw from epoch `{epoch - 2}`"
        )

        slack.send_message(message_slack)

    return double_dead_indexes
