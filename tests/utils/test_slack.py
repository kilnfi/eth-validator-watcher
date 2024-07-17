from eth_validator_watcher import utils
import requests_mock


def test_slack() -> None:
    slack = utils.Slack(
        "MY CHANNEL",
        "https://hooks.slack.com/services/xxxxx/yyy/zzzzzzzzzzzzzzzzzzzzzzzz",
    )
    with requests_mock.Mocker() as mock:
        mock.post(
            "https://hooks.slack.com/services/xxxxx/yyy/zzzzzzzzzzzzzzzzzzzzzzzz",
            status_code=200,
        )
        slack.send_message("MY TEXT")
        assert mock.called
        assert mock.call_count == 1
        assert mock.request_history[0].json() == {"text": "MY TEXT"}
