from eth_validator_watcher.utils import slots
from freezegun import freeze_time
from eth_validator_watcher import utils


def sleep(seconds: int) -> None:
    assert seconds in {11, 23}


utils.sleep = sleep  # type: ignore


@freeze_time("2023-01-01 00:00:13")
def test_slots() -> None:
    iter_slots = iter(slots(1672531200))
    assert next(iter_slots) == (2, 1672531224)
    assert next(iter_slots) == (3, 1672531236)
