from app.cache.ttl_cache import TTLCache
from app.config.settings import settings
from app.exchanges.base import ExchangeAdapter
from app.utils.exchange_mapper import Exchange


class IntradayService:
    def __init__(self, adapter: ExchangeAdapter, cache: TTLCache):
        self.adapter = adapter
        self.cache = cache

    def get_intraday(self, symbol: str, exchange: Exchange, interval: str) -> tuple[list[dict], bool]:
        key = f"intraday:{exchange.value}:{symbol}:{interval}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached, True
        candles = self.adapter.fetch_candles(symbol, exchange, interval=interval, period="1d")
        self.cache.set(key, candles, settings.intraday_ttl_seconds)
        return candles, False
