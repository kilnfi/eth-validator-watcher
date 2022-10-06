import asyncio
import functools
import json
from itertools import count
from pathlib import Path
from typing import Any, List, Optional, Set

import typer
from aiohttp import ClientResponse, ClientSession, ClientTimeout
from aiohttp_sse_client import client
from async_lru import alru_cache
from prometheus_client import Counter, start_http_server
from typer import Option

from .models import Committees, DataBlock, ProposerDuties, SlotWithStatus

NB_SLOT_PER_EPOCH = 32

print = functools.partial(print, flush=True)
app = typer.Typer()


def load_pubkeys_from_file(path: Path) -> set[str]:
    """Load public keys from a file.

    path: A path to a file containing a list of public keys.
    Returns the corresponding set of public keys.
    """
    # Ideally, this function should be async
    with path.open() as file_descriptor:
        return set((f"0x{line.strip()}" for line in file_descriptor))


async def get_with_retry(  # type: ignore
    session: ClientSession, url: str, *args: list[Any], **kwargs: dict[str, Any]
) -> ClientResponse:
    for counter in count(1):
        try:
            return await session.get(url, allow_redirects=True, *args, **kwargs)
        except asyncio.TimeoutError:
            if counter > 3:
                print(f"⚠️      {url} timed out {counter} times")


class Beacon:
    def __init__(self, session: ClientSession, url: str) -> None:
        self.session = session
        self.__url = url

    @alru_cache(maxsize=10)
    async def get_proposer_duties(self, slot_number: int) -> ProposerDuties:
        epoch = slot_number // NB_SLOT_PER_EPOCH

        resp = await get_with_retry(
            self.session,
            f"{self.__url}/eth/v1/validator/duties/proposer/{epoch}",
        )

        proposer_duties_dict = await resp.json()
        return ProposerDuties(**proposer_duties_dict)

    @alru_cache(maxsize=10)
    async def is_block_missed(self, slot_number: int) -> bool:
        current_block = await get_with_retry(
            self.session, f"{self.__url}/eth/v2/beacon/blocks/{slot_number}"
        )

        return current_block.status == 404


class Web3Signer:
    def __init__(self, session: ClientSession, url: str) -> None:
        self.session = session
        self.__url = url

    async def load_pubkeys(self) -> set[str]:
        """Load public keys from Web3Signer.

        session: aiohttp client session
        url: A URL to Web3Signer
        Returns the corresponding set of public keys.
        """
        resp = await get_with_retry(
            self.session, f"{self.__url}/api/v1/eth2/publicKeys"
        )
        return set(await resp.json())


@alru_cache(maxsize=10)
async def get_duty_attestation_slot_to_validator_index(
    session: ClientSession, beacon_url: str, slot_number: int
) -> dict[int, set[int]]:
    epoch = slot_number // NB_SLOT_PER_EPOCH

    resp = await get_with_retry(
        session,
        f"{beacon_url}/eth/v1/beacon/states/head/committees",
        params=dict(epoch=epoch),
    )

    committees_dict = await resp.json()
    committees = Committees(**committees_dict)
    data = committees.data

    return {item.slot: set(item.validators) for item in data}


async def handle_missed_block_detection(
    beacon: Beacon,
    data_block: DataBlock,
    previous_slot_number: int,
    initial_sleep_time_sec: int,
    missed_block_proposals_counter: Counter,
    pubkeys_file_path: Optional[Path],
    web3signers: Set[Web3Signer],
):
    current_slot_number = data_block.slot

    # Normally (according to ConsenSys team), if a block is missed, then there is no
    # event emitted. However, it seems there is some cases where the event is
    # nevertheless emitted. So we check its state.
    # Furthermore, it seems sometimes the route `beacon/blocks/{current_slot_number}`
    # is not ready while the event is triggered, so we wait a little bit.

    await asyncio.sleep(initial_sleep_time_sec)

    is_current_block_missed: bool = await beacon.is_block_missed(current_slot_number)

    slots_with_status = [
        SlotWithStatus(number=slot, missed=True)
        for slot in range(previous_slot_number + 1, current_slot_number)
    ] + [SlotWithStatus(number=current_slot_number, missed=is_current_block_missed)]

    for slot_with_status in slots_with_status:
        proposer_duties: ProposerDuties = await beacon.get_proposer_duties(
            current_slot_number
        )

        # Get proposer public key for this slot
        proposer_duties_data = proposer_duties.data

        # In `data` list, items seems to be ordered by slot.
        # However, there is no specification for that, so it is wiser to
        # iterate on the list
        proposer_public_key = next(
            (
                proposer_duty_data.pubkey
                for proposer_duty_data in proposer_duties_data
                if proposer_duty_data.slot == slot_with_status.number
            )
        )

        # Get public keys to watch from file
        pubkeys_from_file: set[str] = (
            load_pubkeys_from_file(pubkeys_file_path)
            if pubkeys_file_path is not None
            else set()
        )

        # Get public keys to watch from Web3Signer
        pubkeys_from_web3signer: set[str] = set().union(
            *[await web3signer.load_pubkeys() for web3signer in web3signers]
        )

        pubkeys = pubkeys_from_file | pubkeys_from_web3signer

        # Check if the validator who has to propose is ours
        is_our_validator = proposer_public_key in pubkeys
        positive_emoji = "✨" if is_our_validator else "✅"
        negative_emoji = "❌" if is_our_validator else "💩"

        emoji, proposed_or_missed = (
            (negative_emoji, "missed  ")
            if slot_with_status.missed
            else (positive_emoji, "proposed")
        )

        message = (
            f"{emoji} {'Our ' if is_our_validator else '    '}validator "
            f"{proposer_public_key} {proposed_or_missed} block "
            f"{slot_with_status.number} {emoji} - 🔑 {len(pubkeys)} keys watched"
        )

        print(message)

        if is_our_validator and slot_with_status.missed:
            missed_block_proposals_counter.inc()


async def handler_event(
    beacon: Beacon,
    event: client.MessageEvent,
    previous_slot_number: Optional[int],
    pubkeys_file_path: Optional[Path],
    web3signers: Set[Web3Signer],
    missed_block_proposals_counter: Counter,
    initial_sleep_time_sec: int = 1,
) -> int:
    """Handle an event.

    session: A client session
    event: The event to handle
    previous_slot_number: The slot number of latest handled event
    beacon_url: URL of beacon node
    publeys_file_path: A path to a file containing the list of keys to watch (optional)
    web3signer_urls: URLs to Web3Signer instance(s) signing for keys to watch (optional)
    missed_block_proposals_counter: A Prometheus counter for each missed block proposal
    initial_sleep_time_sec: Initial sleep time in seconds (optional)

    Returns the latest slot number handled.
    """

    # Bookkeeping
    # -----------
    data_dict = json.loads(event.data)
    data_block = DataBlock(**data_dict)
    current_slot_number = DataBlock(**data_dict).slot

    previous_slot_number = (
        current_slot_number - 1
        if previous_slot_number is None
        else previous_slot_number
    )

    # Missed block detection
    # ----------------------
    await handle_missed_block_detection(
        beacon,
        data_block,
        previous_slot_number,
        initial_sleep_time_sec,
        missed_block_proposals_counter,
        pubkeys_file_path,
        web3signers,
    )

    return current_slot_number


def write_liveliness_file(liveliness_file: Path):
    """Overwrite liveliness file"""
    liveliness_file.parent.mkdir(exist_ok=True, parents=True)

    with liveliness_file.open("w") as file_descriptor:
        file_descriptor.write("OK")


async def handler_async(
    beacon_url: str,
    pubkeys_file_path: Optional[Path],
    web3signer_urls: Set[str],
    liveliness_file: Optional[Path],
):
    """Asynchronous handler

    beacon_url: The URL of Teku beacon node
    publeys_file_path: A path to a file containing the list of keys to watch (optional)
    web3signer_url: A URL to a Web3Signer instance signing for keys to watch (optional)
    liveliness_file: File overwritten at each epoch (optional)
    """
    missed_block_proposals_counter = Counter(
        "eth_validator_watcher_missed_block_proposals",
        "Ethereum Validator Watcher Missed block proposals",
    )

    async with ClientSession(
        timeout=ClientTimeout(
            total=None, connect=None, sock_connect=None, sock_read=None
        )
    ) as session, client.EventSource(
        f"{beacon_url}/eth/v1/events",
        params=dict(topics="block"),
        session=session,
    ) as event_source:
        beacon = Beacon(session, beacon_url)

        web3signers = {
            Web3Signer(session, web3signer_url) for web3signer_url in web3signer_urls
        }

        previous_slot_number: Optional[int] = None

        async for event in event_source:
            async with ClientSession(
                timeout=ClientTimeout(
                    total=1, connect=None, sock_connect=None, sock_read=None
                )
            ) as session:
                beacon.session = session

                for web3signer in web3signers:
                    web3signer.session = session

                previous_slot_number = await handler_event(
                    beacon,
                    event,
                    previous_slot_number,
                    pubkeys_file_path,
                    web3signers,
                    missed_block_proposals_counter,
                )

            if liveliness_file is not None:
                write_liveliness_file(liveliness_file)


@app.command()
def handler(
    beacon_url: str = Option(..., help="URL of Teku beacon node"),
    pubkeys_file_path: Optional[Path] = Option(
        None,
        help="File containing the list of public keys to watch",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    web3signer_url: Optional[List[str]] = Option(
        None, help="URL to web3signer managing keys to watch"
    ),
    liveliness_file: Optional[Path] = Option(
        None, help="File overwritten at each epoch"
    ),
) -> None:
    """
    🚨 Be alerted when you miss a block proposal! 🚨

    This tool watches the 🥓 Ethereum Beacon chain 🥓 and raises and alert when
    a block proposal is missed. It needs to be connected to a beacon node.

    \b
    You can specify:
    - the path to a file containing the list of public your keys to watch, or / and
    - an URL to a Web3Signer instance managing your keys to watch

    \b
    Pubkeys are load dynamically, at each slot.
    - If you use pubkeys file, you can change it without having to restart the watcher.
    - If you use Web3Signer, a call to Web3Signer will be done at every slot to get the
    latest keys to watch.

    A prometheus counter named `missed_block_proposals` is automatically increased by 1
    when one of your validators missed a block.

    Prometheus server is automatically exposed on port 8000.
    """
    default_set: set[str] = set()

    web3signer_urls = set(web3signer_url) if web3signer_url is not None else default_set
    start_http_server(8000)

    asyncio.run(
        handler_async(beacon_url, pubkeys_file_path, web3signer_urls, liveliness_file)
    )
