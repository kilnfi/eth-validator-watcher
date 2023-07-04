"""Contains the Relays class which is used to interact with the relays."""

from time import sleep
from prometheus_client import Counter
from requests import Session, codes
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import ConnectionError

MAX_TRIALS = 5
WAIT_SEC = 0.5

bad_relay_count = Counter(
    "bad_relay_count",
    "Bad relay count",
)


class Relays:
    """Relays abstraction."""

    def __init__(self, urls: list[str]) -> None:
        """Relays

        Parameters:
        urls: URLs where the relays can be reached
        """
        self.__urls = urls
        self.__http = Session()

        self.__http.mount(
            "http://",
            HTTPAdapter(
                max_retries=Retry(
                    backoff_factor=0.5,
                    total=3,
                    status_forcelist=[codes.not_found],
                )
            ),
        )

    def process(self, slot: int) -> None:
        """Detect if the block was built by a known relay.

        Parameters:
        slot: Slot
        """
        if len(self.__urls) == 0:
            return

        if not any(
            (
                self.__is_proposer_payload_delivered(relay_url, slot)
                for relay_url in self.__urls
            )
        ):
            bad_relay_count.inc()
            print(
                "🟧 Block proposed with unknown builder (may be a locally built block)"
            )

    def __is_proposer_payload_delivered(
        self,
        url: str,
        slot: int,
        trial_count=0,
        wait_sec=WAIT_SEC,
    ) -> bool:
        """Check if the block was built by a known relay.

        Parameters:
        url: URL where the relay can be reached
        slot: Slot
        """
        try:
            response = self.__http.get(
                f"{url}/relay/v1/data/bidtraces/proposer_payload_delivered",
                params=dict(slot=slot),
            )
        except ConnectionError:
            if trial_count >= MAX_TRIALS:
                raise

            sleep(wait_sec)

            return self.__is_proposer_payload_delivered(
                url, slot, trial_count + 1, wait_sec
            )

        response.raise_for_status()
        proposer_payload_delivered_json: list = response.json()

        assert (
            len(proposer_payload_delivered_json) <= 1
        ), "Relay returned more than one block"

        return len(proposer_payload_delivered_json) == 1
