from prometheus_client import Gauge
from requests import Session
from pydantic import parse_obj_as
from .models import CoinbaseTrade

URL = "https://api.pro.coinbase.com/products/ETH-USD/trades"
eth_usd_gauge = Gauge("eth_usd", "ETH/USD conversion rate")


class Coinbase:
    def __init__(self) -> None:
        self.__http = Session()

    def emit_eth_usd_conversion_rate(self) -> None:
        try:
            response = self.__http.get(URL, params=dict(limit=1))
            trades_dict = response.json()
            trades = parse_obj_as(list[CoinbaseTrade], trades_dict)
            trade, *_ = trades
            eth_usd_gauge.set(trade.price)
        except:
            # This feature is totally optional, so if it fails, we just return 0
            pass
