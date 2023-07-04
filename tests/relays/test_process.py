from eth_validator_watcher.relays import Relays, bad_relay_count
from requests_mock import Mocker
from pytest import raises
from requests.exceptions import ConnectionError


def test_process_no_relay() -> None:
    counter_before = bad_relay_count.collect()[0].samples[0].value  # type: ignore
    relays = Relays(urls=[])
    relays.process(slot=42)
    counter_after = bad_relay_count.collect()[0].samples[0].value  # type: ignore

    delta = counter_after - counter_before
    assert delta == 0


def test_process_bad_relay() -> None:
    relays = Relays(urls=["http://relay-1.com", "http://relay-2.com"])

    counter_before = bad_relay_count.collect()[0].samples[0].value  # type: ignore

    with Mocker() as mock:
        mock.get(
            "http://relay-1.com/relay/v1/data/bidtraces/proposer_payload_delivered?slot=42",
            json=[],
        )

        mock.get(
            "http://relay-2.com/relay/v1/data/bidtraces/proposer_payload_delivered?slot=42",
            json=[],
        )

        relays.process(slot=42)

    counter_after = bad_relay_count.collect()[0].samples[0].value  # type: ignore
    delta = counter_after - counter_before
    assert delta == 1


def test_process_good_relay() -> None:
    relays = Relays(urls=["http://relay-1.com", "http://relay-2.com"])

    counter_before = bad_relay_count.collect()[0].samples[0].value  # type: ignore

    with Mocker() as mock:
        mock.get(
            "http://relay-1.com/relay/v1/data/bidtraces/proposer_payload_delivered?slot=42",
            json=[],
        )

        mock.get(
            "http://relay-2.com/relay/v1/data/bidtraces/proposer_payload_delivered?slot=42",
            json=["a block"],
        )

        relays.process(slot=42)

    counter_after = bad_relay_count.collect()[0].samples[0].value  # type: ignore
    delta = counter_after - counter_before
    assert delta == 0


def test_process_relay_bad_answer() -> None:
    relays = Relays(urls=["http://relay.com"])

    with Mocker() as mock:
        mock.get(
            "http://relay.com/relay/v1/data/bidtraces/proposer_payload_delivered?slot=42",
            json=["first block", "second block"],
        )

        with raises(AssertionError):
            relays.process(slot=42)


def test___is_proposer_payload_delivered() -> None:
    relays = Relays(urls=["http://relay.com"])

    with Mocker() as mock:
        mock.get(
            "http://relay.com/relay/v1/data/bidtraces/proposer_payload_delivered?slot=42",
            exc=ConnectionError,
        )

        with raises(ConnectionError):
            relays._Relays__is_proposer_payload_delivered(  # type: ignore
                url="http://relay.com", slot=42, wait_sec=0
            )
