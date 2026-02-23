from app.cache.ttl_cache import TTLCache
from app.config.settings import settings
from app.exchanges.base import ExchangeAdapter
from app.utils.exchange_mapper import Exchange


class QuoteService:
    def __init__(self, adapter: ExchangeAdapter, cache: TTLCache):
        self.adapter = adapter
        self.cache = cache

    def get_quote(self, symbol: str, exchange: Exchange) -> tuple[dict, bool]:
        key = f"quote:{exchange.value}:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached, True
        data = self.adapter.fetch_quote(symbol, exchange)
        self.cache.set(key, data, settings.quote_ttl_seconds)
        return data, False
