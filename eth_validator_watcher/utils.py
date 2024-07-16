import re
from pathlib import Path
from time import sleep, time
from typing import Any, Iterator, Optional, Tuple

import requests

from eth_validator_watcher.models import KeyReporterQueryResponse
from more_itertools import chunked
from prometheus_client import Gauge

from .web3signer import Web3Signer

NB_SLOT_PER_EPOCH = 32
NB_SECOND_PER_SLOT = 12
MISSED_BLOCK_TIMEOUT_SEC = 10
SLOT_FOR_MISSED_ATTESTATIONS_PROCESS = 16
SLOT_FOR_REWARDS_PROCESS = 17
ETH1_ADDRESS_LEN = 40
ETH2_ADDRESS_LEN = 96

CHUCK_NORRIS = [
    "Chuck Norris doesn't stake Ethers; he stares at the blockchain, and it instantly "
    "produces new coins.",
    "When Chuck Norris sends Ethers, it doesn't need confirmations. The Ethereum "
    "network just knows better than to mess with Chuck.",
    "Chuck Norris once hacked into a smart contract without using a computer. He just "
    "stared at the code, and it fixed itself.",
    "Ethereum's gas fees are afraid of Chuck Norris. They lower themselves just to "
    "avoid his wrath.",
    "Chuck Norris doesn't need a private key to access his Ethereum wallet. He just "
    "flexes his biceps, and it opens.",
    "When Chuck Norris trades on a decentralized exchange, the price slippage goes in "
    "his favor, no matter what.",
    "Vitalik Buterin once challenged Chuck Norris to a coding contest. Chuck won by "
    "writing Ethereum's whitepaper with his eyes closed.",
    "Chuck Norris's Ethereum nodes are so fast that they can process transactions "
    "before they even happen.",
    'The Ethereum community calls Chuck Norris the "Smart Contract Whisperer" '
    "because he can make any contract do his bidding.",
    "When Chuck Norris checks his Ethereum balance, the wallet interface just says, "
    '"Infinite."',
]

metric_keys_count = Gauge(
    "keys_count",
    "Keys count",
)


def convert_hex_to_bools(hex: str) -> list[bool]:
    """Convert an hexadecimal number into list of booleans

    Parameters:
    hex: can contain `0x` prefix

    Example:
    --------
    convert_hex_to_bools("0x0F0A") == convert_hex_to_bools("0F0A") == \
    [
        False, False, False, False,
        True, True, True, True,
        False, False, False, False,
        True, False, True, False
    ]
    """
    hex_without_0x_prefix = hex[2:] if hex[:2] == "0x" else hex

    hex_without_0x_prefix_size = len(hex_without_0x_prefix) * 4
    binary = (bin(int(hex_without_0x_prefix, 16))[2:]).zfill(hex_without_0x_prefix_size)

    return [bit == "1" for bit in binary]


def switch_endianness(bits: list[bool]) -> list[bool]:
    """Revert bits by 8 groups

    Paremeters:
    bits: list of booleans representing bits

    Example:
    -------
    switch_endianness(
        [
            False, False, True, False, True, True, True, False,
            True, False, True, False, False, True, True, True
        ]
    ==
        [
            False, True, True, True, False, True, False, False,
            True, True, True, False, False, True, False, True
        ]
    )
    """
    list_of_bits = chunked(bits, 8)
    reversed_list_of_bits = [reversed(bits) for bits in list_of_bits]
    return [item for sublist in reversed_list_of_bits for item in sublist]


def remove_all_items_from_last_true(bits: list[bool]) -> list[bool]:
    """Remove all items after last True

    Paremeters:
    bits: list of booleans representing bits

    If no True is found in the list, StopIteration is raised

    Example:
    --------

    remove_all_items_from_last_true([False, True, False, True, True, False]) == \
        [False, True, False, True]
    """
    try:
        index = next((index for index, bit in enumerate(reversed(bits)) if bit))
    except StopIteration:
        raise StopIteration(f"No `True` detected in {bits}")

    return bits[: -index - 1]


def aggregate_bools(list_of_bools: list[list[bool]]) -> list[bool]:
    """Aggregate bools

    Parameters:
    list_of_bools: A list of list of booleans

    If the length of each list is not the same, `ValueError` is raised.

    examples:
    ---------
    aggregate_bools(
        [
            [False, False, True],
            [False, True, False]
        ]
    ) == [False, True, True]

    aggregate_bools(
    [
        [False, False],
        [False, True, False]
    ]
    ) ==> ValueError
    """

    _, *trash = {len(bits) for bits in list_of_bools}

    if trash != []:
        raise ValueError("At least one bools has not the same length than others")

    return [any(bools) for bools in zip(*list_of_bools)]  # type:ignore


def apply_mask(items: list[Any], mask: list[bool]) -> set[Any]:
    """Apply mask

    Parameters:
    items: A list of items
    mask: A list of booleans representing a mask

    Example:
    --------

    apply_mask(
        ["a", "b", "c", "d", "e"],
        [True, False, False, True, False]
    ) == {"a", "d"}
    """

    return set(item for item, bit in zip(items, mask) if bit)


def load_validator_data_from_file(path: Path) -> dict[str, tuple[str, str]]:
    """Load validator data from a file.

    Parameters:
    path: A path to a file containing a list of validator public keys, deployment IDs, and validator IDs.

    Returns:
    A dictionary where the key is the public key and the value is a tuple containing deployment ID and validator ID.
    """
    with path.open() as file_descriptor:
        # Skip the header
        next(file_descriptor)

        validator_data = {}
        for line in file_descriptor:
            parts = line.strip().split()
            if len(parts) == 3:
                pub_key, deployment_id, validator_id = parts
                pub_key = eth2_address_lower_0x_prefixed(pub_key)
                validator_data[pub_key] = (deployment_id, validator_id)

        return validator_data


def load_validator_data_from_key_reporter(
    pubkeys_url: str,
) -> dict[str, tuple[str, str]]:
    """Load validator data from the key reporter.

    Returns:
    A dictionary where the key is the public key and the value is a tuple containing deployment ID and validator ID.
    """
    headers = {"content-type": "application/json", "user-agent": "hopper-dashboard"}
    response = requests.post(pubkeys_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    key_reporter_response = KeyReporterQueryResponse(**data)
    result = {
        eth2_address_lower_0x_prefixed(validator.validator_public_key): (
            validator.deployment_id,
            validator.validator_id,
        )
        for validator in key_reporter_response.validators
    }

    return result


def get_our_pubkeys(
    pubkeys_url: str,
) -> dict[str, tuple[str, str]]:
    """Get our pubkeys

    Parameters:
    pubkeys_url: The url of the key reporter containing keys to watch

    Query pubkeys from the key reporter and return them as a dictionary.
    If `our_pubkeys` is already set and we are not at the beginning of a new epoch,
    returns `our_pubkeys`.
    """

    # Get public keys to watch from file
    pubkeys_from_key_reporter: dict[str, tuple[str, str]] = (
        load_validator_data_from_key_reporter(pubkeys_url)
        if pubkeys_url is not None
        else set()
    )

    our_pubkeys = pubkeys_from_key_reporter
    metric_keys_count.set(len(our_pubkeys))
    return our_pubkeys


def write_liveness_file(liveness_file: Path):
    """Write liveness file"""
    liveness_file.parent.mkdir(exist_ok=True, parents=True)

    with liveness_file.open("w") as file_descriptor:
        file_descriptor.write("OK")


class Slack:

    def __init__(self, channel: str, webhook_url: str) -> None:
        self.__channel = channel
        self.__webhook_url = webhook_url

    def send_message(self, message: str) -> None:
        payload = {"text": message}
        response = requests.post(self.__webhook_url, json=payload)

        if response.status_code != 200:
            raise ValueError(
                f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}"
            )


def slots(genesis_time_sec: int) -> Iterator[Tuple[int, int]]:
    next_slot = int((time() - genesis_time_sec) / NB_SECOND_PER_SLOT) + 1

    try:
        while True:
            next_slot_time_sec = genesis_time_sec + next_slot * NB_SECOND_PER_SLOT
            time_to_wait = next_slot_time_sec - time()
            sleep(max(0, time_to_wait))

            yield next_slot, next_slot_time_sec

            next_slot += 1
    except KeyboardInterrupt:
        pass  # pragma: no cover


def convert_seconds_to_dhms(seconds: int) -> tuple[int, int, int, int]:
    # Calculate days, hours, minutes, and seconds
    days, seconds = divmod(seconds, 86400)  # 1 day = 24 hours * 60 minutes * 60 seconds
    hours, seconds = divmod(seconds, 3600)  # 1 hour = 60 minutes * 60 seconds
    minutes, seconds = divmod(seconds, 60)  # 1 minute = 60 seconds

    return days, hours, minutes, seconds


def eth1_address_lower_0x_prefixed(address: str) -> str:
    address_lower = address.lower()

    if not re.match(f"^(0x)?[0-9a-f]{{{ETH1_ADDRESS_LEN}}}$", address_lower):
        raise ValueError(f"Invalid ETH1 address: {address_lower}")

    if len(address) == ETH1_ADDRESS_LEN:
        return f"0x{address_lower}"

    return address_lower


def eth2_address_lower_0x_prefixed(address: str) -> str:
    address_lower = address.lower()

    if not re.match(f"^(0x)?[0-9a-f]{{{ETH2_ADDRESS_LEN}}}$", address_lower):
        raise ValueError(f"Invalid ETH2 address: {address_lower}")

    if len(address) == ETH2_ADDRESS_LEN:
        return f"0x{address_lower}"

    return address_lower


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
