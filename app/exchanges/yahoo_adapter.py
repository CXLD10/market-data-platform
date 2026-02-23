from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config.settings import settings
from app.exchanges.base import ExchangeAdapter
from app.utils.exchange_mapper import Exchange, from_provider_symbol, to_provider_symbol
from app.utils.validators import normalize_timestamp, to_native_float, to_native_int


class YahooAdapter(ExchangeAdapter):
    def _retry(self, fn):
        delay = settings.retry_backoff_base_seconds
        last_error = None
        for attempt in range(settings.retry_attempts):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if attempt < settings.retry_attempts - 1:
                    time.sleep(delay)
                    delay *= 2
        raise last_error

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urlencode(params)
        request = Request(f"{url}?{query}", headers={"User-Agent": "market-data-platform/2.0"})
        with urlopen(request, timeout=settings.request_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _fetch_chart(self, provider_symbol: str, interval: str, range_value: str) -> dict[str, Any]:
        payload = self._get_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{provider_symbol}",
            {"interval": interval, "range": range_value},
        )
        return payload["chart"]["result"][0]

    def fetch_quote(self, symbol: str, exchange: Exchange) -> dict[str, Any]:
        provider_symbol = to_provider_symbol(symbol, exchange)

        def _run():
            result = self._fetch_chart(provider_symbol, interval="1m", range_value="1d")
            meta = result.get("meta", {})
            ts = result.get("timestamp", [])
            last_ts = ts[-1] if ts else int(time.time())
            return {
                "price": to_native_float(meta.get("regularMarketPrice")),
                "open": to_native_float(meta.get("chartPreviousClose")),
                "high": to_native_float(meta.get("regularMarketDayHigh")),
                "low": to_native_float(meta.get("regularMarketDayLow")),
                "previous_close": to_native_float(meta.get("previousClose")),
                "volume": to_native_int(meta.get("regularMarketVolume")),
                "currency": str(meta.get("currency") or "USD"),
                "timestamp": normalize_timestamp(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_ts))).isoformat(),
            }

        return self._retry(_run)

    def fetch_candles(self, symbol: str, exchange: Exchange, interval: str, period: str) -> list[dict[str, Any]]:
        provider_symbol = to_provider_symbol(symbol, exchange)

        def _run():
            result = self._fetch_chart(provider_symbol, interval=interval, range_value=period)
            timestamps = result.get("timestamp", [])
            quote = (result.get("indicators", {}).get("quote", [{}]) or [{}])[0]
            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])
            candles: list[dict[str, Any]] = []
            for idx, ts in enumerate(timestamps):
                values = [opens[idx] if idx < len(opens) else None, highs[idx] if idx < len(highs) else None, lows[idx] if idx < len(lows) else None, closes[idx] if idx < len(closes) else None, volumes[idx] if idx < len(volumes) else None]
                if any(v is None for v in values):
                    continue
                candle = {
                    "timestamp": normalize_timestamp(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))).isoformat(),
                    "open": to_native_float(values[0], default=-1),
                    "high": to_native_float(values[1], default=-1),
                    "low": to_native_float(values[2], default=-1),
                    "close": to_native_float(values[3], default=-1),
                    "volume": to_native_int(values[4], default=-1),
                }
                if min(candle["open"], candle["high"], candle["low"], candle["close"], candle["volume"]) < 0:
                    continue
                candles.append(candle)
            candles.sort(key=lambda item: item["timestamp"])
            return candles

        return self._retry(_run)

    def _fetch_quote_summary(self, provider_symbol: str, modules: str) -> dict[str, Any]:
        payload = self._get_json(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{provider_symbol}",
            {"modules": modules},
        )
        return payload["quoteSummary"]["result"][0]

    def fetch_fundamentals(self, symbol: str, exchange: Exchange) -> dict[str, Any]:
        provider_symbol = to_provider_symbol(symbol, exchange)

        def _run():
            result = self._fetch_quote_summary(provider_symbol, "defaultKeyStatistics,financialData,assetProfile,price")
            stats = result.get("defaultKeyStatistics", {})
            fin = result.get("financialData", {})
            profile = result.get("assetProfile", {})
            price = result.get("price", {})
            return {
                "market_cap": to_native_float((price.get("marketCap") or {}).get("raw")),
                "pe_ratio": to_native_float((stats.get("trailingPE") or {}).get("raw")),
                "forward_pe": to_native_float((stats.get("forwardPE") or {}).get("raw")),
                "eps": to_native_float((stats.get("trailingEps") or {}).get("raw")),
                "revenue": to_native_float((fin.get("totalRevenue") or {}).get("raw")),
                "revenue_growth": to_native_float((fin.get("revenueGrowth") or {}).get("raw")),
                "ebitda": to_native_float((fin.get("ebitda") or {}).get("raw")),
                "net_income": to_native_float((fin.get("netIncomeToCommon") or {}).get("raw")),
                "debt_to_equity": to_native_float((fin.get("debtToEquity") or {}).get("raw")),
                "roe": to_native_float((fin.get("returnOnEquity") or {}).get("raw")),
                "sector": str(profile.get("sector") or "Unknown"),
                "industry": str(profile.get("industry") or "Unknown"),
                "country": str(profile.get("country") or "Unknown"),
                "currency": str(price.get("currency") or "USD"),
            }

        return self._retry(_run)

    def fetch_company(self, symbol: str, exchange: Exchange) -> dict[str, Any]:
        provider_symbol = to_provider_symbol(symbol, exchange)

        def _run():
            result = self._fetch_quote_summary(provider_symbol, "assetProfile,price")
            profile = result.get("assetProfile", {})
            price = result.get("price", {})
            return {
                "company_name": str(price.get("longName") or symbol),
                "sector": str(profile.get("sector") or "Unknown"),
                "industry": str(profile.get("industry") or "Unknown"),
                "description": str(profile.get("longBusinessSummary") or ""),
                "website": str(profile.get("website") or ""),
                "market_cap": to_native_float((price.get("marketCap") or {}).get("raw")),
            }

        return self._retry(_run)

    def search(self, query: str) -> list[dict[str, Any]]:
        def _run():
            payload = self._get_json(
                "https://query1.finance.yahoo.com/v1/finance/search",
                {"q": query, "quotesCount": 10, "newsCount": 0},
            )
            results: list[dict[str, Any]] = []
            for quote in payload.get("quotes", []):
                provider_symbol = str(quote.get("symbol") or "")
                if not provider_symbol:
                    continue
                clean_symbol, exchange = from_provider_symbol(provider_symbol)
                results.append(
                    {
                        "symbol": clean_symbol,
                        "exchange": exchange.value,
                        "company_name": str(quote.get("shortname") or quote.get("longname") or clean_symbol),
                        "sector": "Unknown",
                        "currency": str(quote.get("currency") or "USD"),
                    }
                )
            return results

        return self._retry(_run)
