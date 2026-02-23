from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.utils.exchange_mapper import Exchange


class ExchangeAdapter(ABC):
    @abstractmethod
    def fetch_quote(self, symbol: str, exchange: Exchange) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_candles(self, symbol: str, exchange: Exchange, interval: str, period: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_fundamentals(self, symbol: str, exchange: Exchange) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_company(self, symbol: str, exchange: Exchange) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError
