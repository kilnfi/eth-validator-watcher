import json
from pathlib import Path

from aiohttp import ClientSession, web
from aiohttp_sse_client import client
from prometheus_client import Counter
from pytest import fixture
from eth_validator_watcher.tests import assets

from ..entrypoint import handler_event


@fixture
def assets_dir() -> Path:
    return Path(assets.__file__).parent


@fixture
def event_209349() -> client.MessageEvent:
    return client.MessageEvent(
        type="block",
        message="block",
        data='{"slot":"209349","block":"0x81167b7211dcdb45a418f8baf7caa5d20b175789bb61f762e064ae2fe61cc26f","execution_optimistic":false}',
        origin="http://localhost:5051",
        last_event_id="",
    )


@fixture
def pubkeys_file_path(assets_dir: Path) -> Path:
    return assets_dir / "pubkeys.txt"


@fixture
def proposer_duties_6542(assets_dir: Path) -> dict:
    with (assets_dir / "proposer_duties_6542.json").open() as file_descriptor:
        return json.load(file_descriptor)


@fixture
def counter() -> Counter:
    return Counter("test_counter", "Test Counter")


@fixture
async def session(proposer_duties_6542: dict, aiohttp_client) -> ClientSession:
    app = web.Application()

    async def proposer_duties_6542_response(request):
        return web.Response(
            body=json.dumps(proposer_duties_6542), content_type="application/json"
        )

    app.router.add_route(
        "GET",
        "/:5051/eth/v1/validator/duties/proposer/6542",
        proposer_duties_6542_response,
    )

    async def web3signer_public_keys_response(request):
        return web.Response(
            body=json.dumps(
                [
                    "0xb2c191d34c9d09efb42164be35cd04f26d795d2558b0894286e455f8e8b0977d0714e5c8d3596282a434a5efa5248fc5"
                ]
            ),
            content_type="application/json",
        )

    app.router.add_route(
        "GET",
        "/:9000/api/v1/eth2/publicKeys",
        web3signer_public_keys_response,
    )

    return await aiohttp_client(app)


async def test_handler_event(
    event_209349: dict,
    counter: Counter,
    session: ClientSession,
    pubkeys_file_path: Path,
) -> None:
    assert counter.collect()[0].samples[0].value == 0.0

    assert (
        await handler_event(event_209349, None, session, "", None, None, counter)
        == 209349
    )
    assert counter.collect()[0].samples[0].value == 0.0

    assert (
        await handler_event(event_209349, 209348, session, "", None, None, counter)
        == 209349
    )
    assert counter.collect()[0].samples[0].value == 0.0

    assert (
        await handler_event(event_209349, 209347, session, "", None, None, counter)
        == 209349
    )
    assert counter.collect()[0].samples[0].value == 0.0

    assert (
        await handler_event(
            event_209349, 209347, session, "", pubkeys_file_path, None, counter
        )
        == 209349
    )
    assert counter.collect()[0].samples[0].value == 1.0

    assert (
        await handler_event(event_209349, 209347, session, "", None, "", counter)
        == 209349
    )
    assert counter.collect()[0].samples[0].value == 2.0
