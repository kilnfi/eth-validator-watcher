from requests_mock import Mocker

from eth_validator_watcher.coinbase import Coinbase, metric_eth_usd_gauge


def test_emit_eth_usd_conversion_rate_success() -> None:
    coinbase = Coinbase()

    with Mocker() as mock:
        mock.get(
            "https://api.pro.coinbase.com/products/ETH-USD/trades?limit=1",
            json=[
                {
                    "time": "2023-05-25T15:56:17.463034Z",
                    "trade_id": 452598471,
                    "price": "1791.86000000",
                    "size": "1.21500994",
                    "side": "sell",
                }
            ],
        )

        coinbase.emit_eth_usd_conversion_rate()
        assert metric_eth_usd_gauge.collect()[0].samples[0].value == 1791.86  # type: ignore


def test_emit_eth_usd_conversion_rate_error() -> None:
    coinbase = Coinbase()

    with Mocker() as mock:
        mock.get(
            "https://api.pro.coinbase.com/products/ETH-USD/trades?limit=1",
            json=[
                {
                    "time": "2023-05-25T15:56:17.463034Z",
                    "trade_id": 452598471,
                    "NOT A PRICE": "1791.86000000",
                    "size": "1.21500994",
                    "side": "sell",
                }
            ],
        )

        coinbase.emit_eth_usd_conversion_rate()

    # We do not assert nothing special here. We just want to make sure that
    # `emit_eth_usd_conversion_rate` does not raise any exception.
