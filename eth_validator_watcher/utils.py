from pathlib import Path
from typing import Any, Optional

from more_itertools import chunked

from .web3signer import Web3Signer

NB_SLOT_PER_EPOCH = 32


def convert_hex_to_bools(hex: str) -> list[bool]:
    """Convert an hexadecimal number into list of booleans
    `hex` can contain `0x` prefix

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

    Example:
    --------

    apply_mask(
        ["a", "b", "c", "d", "e"],
        [True, False, False, True, False]
    ) == {"a", "d"}
    """

    return set(item for item, bit in zip(items, mask) if bit)


def load_pubkeys_from_file(path: Path) -> set[str]:
    """Load public keys from a file.

    path: A path to a file containing a list of public keys.
    Returns the corresponding set of public keys.
    """
    with path.open() as file_descriptor:
        return set((f"0x{line.strip()}" for line in file_descriptor))


def get_our_pubkeys(
    pubkeys_file_path: Optional[Path],
    web3signers: set[Web3Signer],
    our_pubkeys: Optional[set[str]],
    slot: int,
) -> set[str]:
    """Get our pubkeys

    Query pubkeys from either file path or Web3Signer instance.
    If `our_pubkeys` is already set and we are not at the beginning of a new epoch,
    returns `our_pubkeys`.

    pubkeys_file_path: The path of file containing keys to watch
    web3signers: A set of Web3Signer instance signing for the keys to watch
    our_pubkey: The set containing pubkey to watch]
    slot: Data Slot
    """

    if our_pubkeys is not None and slot % NB_SLOT_PER_EPOCH != 0:
        return our_pubkeys

    # Get public keys to watch from file
    pubkeys_from_file: set[str] = (
        load_pubkeys_from_file(pubkeys_file_path)
        if pubkeys_file_path is not None
        else set()
    )

    pubkeys_from_web3signer: set[str] = set().union(
        *(web3signer.load_pubkeys() for web3signer in web3signers)
    )

    return pubkeys_from_file | pubkeys_from_web3signer


def write_liveliness_file(liveliness_file: Path):
    """Overwrite liveliness file"""
    liveliness_file.parent.mkdir(exist_ok=True, parents=True)

    with liveliness_file.open("w") as file_descriptor:
        file_descriptor.write("OK")
