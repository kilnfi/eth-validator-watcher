import re
from pathlib import Path
from time import sleep, time
from typing import Any, Iterator, List, Optional, Tuple

from more_itertools import chunked
from prometheus_client import Gauge
from slack_sdk import WebClient

from .config import WatchedKeyConfig

# Slots at which processing is performed.
SLOT_FOR_CONFIG_RELOAD = 15
SLOT_FOR_MISSED_ATTESTATIONS_PROCESS = 16
SLOT_FOR_REWARDS_PROCESS = 17

# Default set of existing scopes.
LABEL_SCOPE_NETWORK="scope:network"
LABEL_SCOPE_WATCHED="scope:watched"
LABEL_SCOPE_UNWATCHED="scope:all-network"


def pct(a: int, b: int, inclusive: bool=False) -> float:
    """Helper function to calculate the percentage of a over b.
    """
    total = a + b if not inclusive else b
    if total == 0:
        return 0.0
    return float(a / total) * 100.0


class LimitedDict:
    def __init__(self, max_size: int) -> None:
        assert max_size >= 0, "max_size must be non-negative"

        self.__max_size = max_size
        self.__dict: dict[Any, Any] = dict()

    def __setitem__(self, key: Any, value: Any) -> None:
        self.__dict[key] = value

        first_keys = sorted(self.__dict)[: -self.__max_size]
        for key in first_keys:
            self.__dict.pop(key)

    def __getitem__(self, key: Any) -> Any:
        return self.__dict[key]

    def __contains__(self, key: Any) -> bool:
        return key in self.__dict

    def __len__(self) -> int:
        return len(self.__dict)
