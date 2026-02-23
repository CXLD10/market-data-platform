from app.cache.ttl_cache import TTLCache
from app.config.settings import settings
from app.exchanges.base import ExchangeAdapter
from app.utils.exchange_mapper import Exchange


class HistoricalService:
    def __init__(self, adapter: ExchangeAdapter, cache: TTLCache):
        self.adapter = adapter
        self.cache = cache

    def get_historical(self, symbol: str, exchange: Exchange, period: str, interval: str = "1d") -> tuple[list[dict], bool]:
        key = f"historical:{exchange.value}:{symbol}:{period}:{interval}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached, True
        candles = self.adapter.fetch_candles(symbol, exchange, interval=interval, period=period)
        self.cache.set(key, candles, settings.historical_ttl_seconds)
        return candles, False
