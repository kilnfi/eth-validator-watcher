"""Helper to fetch the ETH/USD price from Coinbase."""

from cachetools import func
from pydantic import parse_obj_as
from requests import Session

from .models import CoinbaseTrade


URL = "https://api.exchange.coinbase.com/products/ETH-USD/trades"


@func.ttl_cache(ttl=600)
def get_current_eth_price() -> float:
    """Get the current ETH price in USD from Coinbase.

    Args:
        None

    Returns:
        float
            The current ETH price in USD, or 0.0 if fetching fails.
    """
    try:
        response = Session().get(URL, params=dict(limit=1))
        trades_dict = response.json()
        trades = parse_obj_as(list[CoinbaseTrade], trades_dict)
        trade, *_ = trades
    except Exception:
        # This feature is totally optional, so if it fails, we just
        # return 0.0.
        return 0.0

    return trade.price
