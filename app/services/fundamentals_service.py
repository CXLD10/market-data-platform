from app.cache.ttl_cache import TTLCache
from app.config.settings import settings
from app.exchanges.base import ExchangeAdapter
from app.utils.exchange_mapper import Exchange


class FundamentalsService:
    def __init__(self, adapter: ExchangeAdapter, cache: TTLCache):
        self.adapter = adapter
        self.cache = cache

    def get_fundamentals(self, symbol: str, exchange: Exchange) -> tuple[dict, bool]:
        key = f"fundamentals:{exchange.value}:{symbol}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached, True
        data = self.adapter.fetch_fundamentals(symbol, exchange)
        self.cache.set(key, data, settings.fundamentals_ttl_seconds)
        return data, False

    def get_company(self, symbol: str, exchange: Exchange) -> tuple[dict, bool]:
        key = f"company:{exchange.value}:{symbol}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached, True
        data = self.adapter.fetch_company(symbol, exchange)
        self.cache.set(key, data, settings.company_ttl_seconds)
        return data, False
