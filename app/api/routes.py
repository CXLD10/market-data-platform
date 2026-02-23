from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from app.cache.ttl_cache import TTLCache
from app.config.settings import settings
from app.exchanges.yahoo_adapter import YahooAdapter
from app.internal_metrics import MetricsCollector
from app.resilience_circuit_breaker import ExchangeCircuitBreaker
from app.schemas.candle import CandleResponseSchema
from app.schemas.company import CompanySchema
from app.schemas.fundamentals import FundamentalsSchema
from app.schemas.quote import QuoteSchema
from app.schemas.symbol import SearchResultSchema
from app.services.fundamentals_service import FundamentalsService
from app.services.historical_service import HistoricalService
from app.services.intraday_service import IntradayService
from app.services.quote_service import QuoteService
from app.services.search_service import SearchService
from app.utils.exchange_mapper import Exchange
from app.utils.market_status import get_market_status
from app.utils.symbol_normalizer import normalize_exchange, normalize_symbol
from app.utils.validators import is_valid_price, sanitize_candles

logger = logging.getLogger(__name__)
router = APIRouter()

cache = TTLCache()
adapter = YahooAdapter()
quote_service = QuoteService(adapter, cache)
intraday_service = IntradayService(adapter, cache)
historical_service = HistoricalService(adapter, cache)
fundamentals_service = FundamentalsService(adapter, cache)
search_service = SearchService(adapter)
metrics = MetricsCollector()
circuit_breaker = ExchangeCircuitBreaker(
    failure_threshold=settings.circuit_failure_threshold,
    recovery_timeout_seconds=settings.circuit_recovery_timeout_seconds,
    half_open_max_attempts=settings.circuit_half_open_max_attempts,
)

_request_buckets: dict[str, deque[float]] = defaultdict(deque)


def error_response(error_code: str, message: str, exchange: str | None = None, status_code: int = 400):
    payload = {
        "schema_version": settings.schema_version,
        "status": "error",
        "error_code": error_code,
        "message": message,
    }
    if exchange:
        payload["exchange"] = exchange
    return JSONResponse(payload, status_code=status_code)


def _degraded_from_cache(cache_key: str, exchange: Exchange, symbol: str, schema_cls, **base):
    cached = cache.get(cache_key)
    if cached:
        payload = {
            "schema_version": settings.schema_version,
            "exchange": exchange.value,
            "symbol": symbol,
            "data_source": "cache",
            "exchange_status": "degraded",
            **base,
            **cached,
        }
        return schema_cls(**payload), True
    return None, False


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = _request_buckets[ip]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_requests_per_minute:
            return error_response("RATE_LIMITED", "Too many requests", status_code=429)
        bucket.append(now)

        response = None
        start = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_complete",
                extra={
                    "request_id": request_id,
                    "exchange": request.query_params.get("exchange", ""),
                    "symbol": request.query_params.get("symbol", ""),
                    "circuit_state": circuit_breaker.state(request.query_params.get("exchange", "NASDAQ")).value if request.query_params.get("exchange") else "NA",
                    "latency_ms": latency_ms,
                    "cache_hit": response.headers.get("x-cache-hit") if response else None,
                    "error_code": response.headers.get("x-error-code") if response else None,
                },
            )

    app.include_router(router)
    return app


@router.get("/health")
def health():
    return {"schema_version": settings.schema_version, "status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/readiness")
def readiness():
    return {"schema_version": settings.schema_version, "status": "ready", "cache": cache.metrics()}


@router.get("/metrics")
def all_metrics():
    output = metrics.global_metrics()
    output["schema_version"] = settings.schema_version
    return output


@router.get("/exchanges/status")
def exchanges_status():
    out = {}
    per_ex = metrics.exchange_status()
    cb = circuit_breaker.snapshot()
    for ex in [Exchange.NSE.value, Exchange.BSE.value, Exchange.NASDAQ.value]:
        item = per_ex.get(ex, {"failure_rate": 0.0, "average_latency_ms": 0.0})
        state = cb.get(ex, {}).get("state", "CLOSED")
        out[ex] = {
            "state": state,
            "failure_rate": item["failure_rate"],
            "average_latency_ms": item["average_latency_ms"],
        }
    return {"schema_version": settings.schema_version, **out}


@router.get("/market-status")
def market_status(exchange: str):
    clean_exchange = normalize_exchange(exchange)
    return {"schema_version": settings.schema_version, **get_market_status(clean_exchange)}


@router.get("/quote", response_model=QuoteSchema)
def quote(symbol: str = Query(...), exchange: str = Query("NASDAQ")):
    start = time.perf_counter()
    try:
        clean_symbol = normalize_symbol(symbol)
        clean_exchange = normalize_exchange(exchange)
    except ValueError:
        return error_response("INVALID_INPUT", "Invalid symbol or exchange", exchange=exchange)

    cache_key = f"quote:{clean_exchange.value}:{clean_symbol}"

    if not circuit_breaker.can_execute(clean_exchange.value):
        degraded, hit = _degraded_from_cache(cache_key, clean_exchange, clean_symbol, QuoteSchema)
        metrics.record_request(clean_exchange.value, success=bool(degraded), latency_ms=(time.perf_counter() - start) * 1000, cache_hit=hit)
        if degraded:
            return degraded
        return error_response("EXCHANGE_UNAVAILABLE", "Exchange temporarily unavailable", exchange=clean_exchange.value, status_code=503)

    try:
        data, hit = quote_service.get_quote(clean_symbol, clean_exchange)
        if not is_valid_price(data.get("price", -1)):
            raise ValueError("invalid price")
        circuit_breaker.record_success(clean_exchange.value)
        metrics.record_request(clean_exchange.value, success=True, latency_ms=(time.perf_counter() - start) * 1000, cache_hit=hit)
        return QuoteSchema(schema_version=settings.schema_version, exchange=clean_exchange.value, symbol=clean_symbol, **data)
    except Exception:
        circuit_breaker.record_failure(clean_exchange.value)
        degraded, hit = _degraded_from_cache(cache_key, clean_exchange, clean_symbol, QuoteSchema)
        metrics.record_request(clean_exchange.value, success=bool(degraded), latency_ms=(time.perf_counter() - start) * 1000, cache_hit=hit)
        if degraded:
            return degraded
        return error_response("EXCHANGE_UNAVAILABLE", "Exchange temporarily unavailable", exchange=clean_exchange.value, status_code=503)


@router.get("/intraday", response_model=CandleResponseSchema)
def intraday(symbol: str, exchange: str, interval: str = "5m"):
    clean_symbol = normalize_symbol(symbol)
    clean_exchange = normalize_exchange(exchange)
    cache_key = f"intraday:{clean_exchange.value}:{clean_symbol}:{interval}"

    if not circuit_breaker.can_execute(clean_exchange.value):
        degraded, _ = _degraded_from_cache(cache_key, clean_exchange, clean_symbol, CandleResponseSchema, interval=interval, candles=[])
        if degraded:
            return degraded
        return error_response("EXCHANGE_UNAVAILABLE", "Exchange temporarily unavailable", exchange=clean_exchange.value, status_code=503)

    try:
        candles, _ = intraday_service.get_intraday(clean_symbol, clean_exchange, interval)
        candles = sanitize_candles(candles)
        circuit_breaker.record_success(clean_exchange.value)
        return CandleResponseSchema(schema_version=settings.schema_version, exchange=clean_exchange.value, symbol=clean_symbol, interval=interval, candles=candles)
    except Exception:
        circuit_breaker.record_failure(clean_exchange.value)
        degraded, _ = _degraded_from_cache(cache_key, clean_exchange, clean_symbol, CandleResponseSchema, interval=interval, candles=[])
        if degraded:
            return degraded
        return error_response("EXCHANGE_UNAVAILABLE", "Exchange temporarily unavailable", exchange=clean_exchange.value, status_code=503)


@router.get("/historical", response_model=CandleResponseSchema)
def historical(symbol: str, exchange: str, period: str = "6mo", interval: str = "1d"):
    clean_symbol = normalize_symbol(symbol)
    clean_exchange = normalize_exchange(exchange)
    cache_key = f"historical:{clean_exchange.value}:{clean_symbol}:{period}:{interval}"

    if not circuit_breaker.can_execute(clean_exchange.value):
        degraded, _ = _degraded_from_cache(cache_key, clean_exchange, clean_symbol, CandleResponseSchema, interval=interval, candles=[])
        if degraded:
            return degraded
        return error_response("EXCHANGE_UNAVAILABLE", "Exchange temporarily unavailable", exchange=clean_exchange.value, status_code=503)

    try:
        candles, _ = historical_service.get_historical(clean_symbol, clean_exchange, period, interval)
        candles = sanitize_candles(candles)
        circuit_breaker.record_success(clean_exchange.value)
        return CandleResponseSchema(schema_version=settings.schema_version, exchange=clean_exchange.value, symbol=clean_symbol, interval=interval, candles=candles)
    except Exception:
        circuit_breaker.record_failure(clean_exchange.value)
        degraded, _ = _degraded_from_cache(cache_key, clean_exchange, clean_symbol, CandleResponseSchema, interval=interval, candles=[])
        if degraded:
            return degraded
        return error_response("EXCHANGE_UNAVAILABLE", "Exchange temporarily unavailable", exchange=clean_exchange.value, status_code=503)


@router.get("/fundamentals", response_model=FundamentalsSchema)
def fundamentals(symbol: str, exchange: str):
    clean_symbol = normalize_symbol(symbol)
    clean_exchange = normalize_exchange(exchange)
    data, _ = fundamentals_service.get_fundamentals(clean_symbol, clean_exchange)
    return FundamentalsSchema(schema_version=settings.schema_version, exchange=clean_exchange.value, symbol=clean_symbol, **data)


@router.get("/company", response_model=CompanySchema)
def company(symbol: str, exchange: str):
    clean_symbol = normalize_symbol(symbol)
    clean_exchange = normalize_exchange(exchange)
    data, _ = fundamentals_service.get_company(clean_symbol, clean_exchange)
    return CompanySchema(schema_version=settings.schema_version, exchange=clean_exchange.value, symbol=clean_symbol, **data)


@router.get("/search", response_model=list[SearchResultSchema])
def search(query: str):
    return [SearchResultSchema(schema_version=settings.schema_version, **item) for item in search_service.search(query)]


@router.get("/price/latest")
def price_latest(symbol: str, exchange: str = "NASDAQ"):
    return quote(symbol=symbol, exchange=exchange)


@router.get("/candles", response_model=CandleResponseSchema)
def candles(symbol: str, exchange: str = "NASDAQ", interval: str = "5m", period: str = "1d"):
    return historical(symbol=symbol, exchange=exchange, period=period, interval=interval)


@router.get("/symbols")
def symbols(query: str = "", limit: int = 25):
    results = search(query) if query else []
    return {"schema_version": settings.schema_version, "symbols": results[:limit], "count": len(results[:limit])}
