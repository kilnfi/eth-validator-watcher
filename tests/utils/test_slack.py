from eth_validator_watcher import utils


class WebClient:
    def __init__(self, token: str):
        assert token == "my_slack_token"

    def chat_postMessage(self, channel: str, text: str):
        assert channel == "MY CHANNEL"
        assert text == "MY TEXT"


utils.WebClient = WebClient  # type: ignore


def test_slack() -> None:
    slack = utils.Slack("MY CHANNEL", "my_slack_token")
    slack.send_message("MY TEXT")
