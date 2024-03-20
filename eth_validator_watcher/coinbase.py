"""Contains the Coinbase class, which is responsible for fetching the ETH/USD"""

from prometheus_client import Gauge
from pydantic import parse_obj_as
from requests import Session

from .models import CoinbaseTrade

URL = "https://api.pro.coinbase.com/products/ETH-USD/trades"
metric_eth_usd_gauge = Gauge("eth_usd", "ETH/USD conversion rate")


class Coinbase:
    """Coinbase abstraction."""

    def __init__(self) -> None:
        """Coinbase"""
        self.__http = Session()

    def emit_eth_usd_conversion_rate(self) -> None:
        """Emit the ETH/USD conversion rate to Prometheus Gauge.

        If any error, fails silently.
        """
        try:
            response = self.__http.get(URL, params=dict(limit=1))
            trades_dict = response.json()
            trades = parse_obj_as(list[CoinbaseTrade], trades_dict)
            trade, *_ = trades
            metric_eth_usd_gauge.set(trade.price)
        except:
            # This feature is totally optional, so if it fails, we just return 0
            pass
