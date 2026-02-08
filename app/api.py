"""
FastAPI REST API endpoints.
Provides stable interfaces for downstream consumers.
"""
from datetime import datetime, timezone, timedelta
import logging
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, Depends, HTTPException, Query, Request as FastAPIRequest
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import text, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Symbol, Trade, Candle
from app.config import settings
from app.observability import observability, RequestTimer
from app.schemas import (
    HealthResponse,
    SymbolResponse,
    SymbolsListResponse,
    PriceResponse,
    TradeResponse,
    TradesListResponse,
    CandleResponse,
    CandlesListResponse,
    ErrorResponse,
    IngestionStatusResponse,
    MetricsResponse,
    RootResponse,
)

logger = logging.getLogger(__name__)

MAX_TRADE_LIMIT = 1000
DEFAULT_TRADE_LIMIT = 100
MAX_SYMBOLS_LIMIT = 500
DEFAULT_SYMBOLS_LIMIT = 100
MAX_CANDLE_LIMIT = 5000
DEFAULT_CANDLE_LIMIT = 500
SUPPORTED_INTERVALS = {"1m": timedelta(minutes=1)}
SYMBOL_PATTERN = r"^[A-Za-z0-9._-]{1,16}$"
REDOC_ASSET_PATH = "/redoc-assets/redoc.standalone.js"
REDOC_BUNDLE_URLS = (
    "https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js",
    "https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
)
_redoc_bundle_cache: bytes | None = None
_redoc_bundle_lock = Lock()

# Create FastAPI app
api = FastAPI(
    title="Market Data Platform",
    description=(
        "Authoritative source for financial price information.\n\n"
        "All endpoints are read-only and return UTC timestamps. "
        "Errors use the standardized shape `{error, details, status}`."
    ),
    version="1.0.0",
    redoc_url=None,
)


ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Bad request",
        "content": {"application/json": {"example": {"error": "request_failed", "details": "start must be before end", "status": 400}}},
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource not found",
        "content": {"application/json": {"example": {"error": "request_failed", "details": "Symbol XYZ not found", "status": 404}}},
    },
    422: {
        "model": ErrorResponse,
        "description": "Validation error",
        "content": {"application/json": {"example": {"error": "validation_error", "details": "[{'loc': ['query', 'symbol'], 'msg': 'String should match pattern'}]", "status": 422}}},
    },
    500: {
        "model": ErrorResponse,
        "description": "Internal server error",
        "content": {"application/json": {"example": {"error": "internal_server_error", "details": "Unexpected server error", "status": 500}}},
    },
}


def _load_redoc_bundle() -> bytes:
    """Download and cache the ReDoc bundle for same-origin serving."""
    global _redoc_bundle_cache
    with _redoc_bundle_lock:
        if _redoc_bundle_cache is not None:
            return _redoc_bundle_cache

        for url in REDOC_BUNDLE_URLS:
            try:
                request = Request(url, headers={"User-Agent": "market-data-platform/1.0"})
                with urlopen(request, timeout=8) as response:
                    payload = response.read()

                if payload:
                    _redoc_bundle_cache = payload
                    logger.info("Loaded ReDoc bundle", extra={"url": url, "size": len(payload)})
                    return payload
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                logger.warning(f"Failed to load ReDoc bundle from {url}: {exc}")

    raise HTTPException(status_code=503, detail="Unable to load ReDoc assets")


def _custom_openapi():
    """Pin OpenAPI output to 3.0.3 for ReDoc compatibility."""
    if api.openapi_schema:
        return api.openapi_schema

    schema = get_openapi(
        title=api.title,
        version=api.version,
        description=api.description,
        routes=api.routes,
    )
    schema["openapi"] = "3.0.3"
    api.openapi_schema = schema
    return api.openapi_schema


api.openapi = _custom_openapi


@api.get(REDOC_ASSET_PATH, include_in_schema=False)
async def redoc_bundle():
    """Serve ReDoc JavaScript from this service to avoid client-side CDN blocks."""
    return Response(content=_load_redoc_bundle(), media_type="application/javascript")


@api.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Serve ReDoc HTML pointing to same-origin JavaScript asset."""
    return get_redoc_html(
        openapi_url=api.openapi_url,
        title=f"{api.title} - ReDoc",
        redoc_js_url=REDOC_ASSET_PATH,
        with_google_fonts=False,
    )




def _flatten_validation_errors(exc: RequestValidationError) -> str:
    """Return a concise, stable validation message string."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(i) for i in err.get("loc", []) if i != "body")
        msg = err.get("msg", "Invalid value")
        parts.append(f"{loc}: {msg}")
    return "; ".join(parts)


@api.exception_handler(HTTPException)
async def http_exception_handler(_: FastAPIRequest, exc: HTTPException):
    details = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    payload = ErrorResponse(error="request_failed", details=details, status=exc.status_code)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@api.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: FastAPIRequest, exc: RequestValidationError):
    payload = ErrorResponse(error="validation_error", details=_flatten_validation_errors(exc), status=422)
    return JSONResponse(status_code=422, content=payload.model_dump())


@api.exception_handler(Exception)
async def unhandled_exception_handler(_: FastAPIRequest, exc: Exception):
    logger.error(f"Unhandled API exception: {exc}", exc_info=True)
    payload = ErrorResponse(error="internal_server_error", details="Unexpected server error", status=500)
    return JSONResponse(status_code=500, content=payload.model_dump())


@api.middleware("http")
async def measure_request_latency(request: FastAPIRequest, call_next):
    """Capture basic request latency metrics for all API calls."""
    timer = RequestTimer()
    response = await call_next(request)
    observability.mark_request_timing(timer.elapsed_ms())
    return response


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _validate_symbol(db: Session, symbol: str) -> str:
    normalized = symbol.upper()
    symbol_obj = db.query(Symbol).filter_by(symbol=normalized).first()
    if not symbol_obj:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return normalized


def _validate_time_range(start: datetime, end: datetime):
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(status_code=400, detail="start and end must include timezone information")
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")


def _validate_interval(interval: str) -> timedelta:
    if interval not in SUPPORTED_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval '{interval}'. Supported values: {', '.join(SUPPORTED_INTERVALS.keys())}"
        )
    return SUPPORTED_INTERVALS[interval]


def _align_to_interval(ts: datetime, bucket_size: timedelta) -> datetime:
    ts_utc = _ensure_utc(ts)
    total_seconds = int(bucket_size.total_seconds())
    floored = int(ts_utc.timestamp()) - (int(ts_utc.timestamp()) % total_seconds)
    return datetime.fromtimestamp(floored, tz=timezone.utc)


def _compute_candles_from_trades(
    db: Session,
    symbol: str,
    interval: str,
    bucket_size: timedelta,
    start: datetime,
    end: datetime,
):
    """Compute and persist candles for the requested range using a single trade scan."""
    aligned_start = _align_to_interval(start, bucket_size)

    trades = (
        db.query(Trade)
        .filter(
            and_(
                Trade.symbol == symbol,
                Trade.timestamp >= aligned_start,
                Trade.timestamp < end,
            )
        )
        .order_by(Trade.timestamp.asc(), Trade.id.asc())
        .all()
    )

    if not trades:
        return

    bucket_data = {}
    for trade in trades:
        bucket_start = _align_to_interval(trade.timestamp, bucket_size)
        if bucket_start not in bucket_data:
            bucket_data[bucket_start] = {
                "open_price": trade.price,
                "high_price": trade.price,
                "low_price": trade.price,
                "close_price": trade.price,
                "volume": float(trade.volume),
                "trade_count": 1,
            }
            continue

        bucket = bucket_data[bucket_start]
        bucket["high_price"] = max(bucket["high_price"], trade.price)
        bucket["low_price"] = min(bucket["low_price"], trade.price)
        bucket["close_price"] = trade.price
        bucket["volume"] += float(trade.volume)
        bucket["trade_count"] += 1

    bucket_timestamps = sorted(bucket_data.keys())
    existing_candles = (
        db.query(Candle)
        .filter(
            and_(
                Candle.symbol == symbol,
                Candle.interval == interval,
                Candle.timestamp.in_(bucket_timestamps),
            )
        )
        .all()
    )
    existing_by_timestamp = {c.timestamp: c for c in existing_candles}

    for bucket_start in bucket_timestamps:
        values = bucket_data[bucket_start]
        candle = existing_by_timestamp.get(bucket_start)
        if not candle:
            candle = Candle(symbol=symbol, interval=interval, timestamp=bucket_start)
            db.add(candle)

        candle.open_price = values["open_price"]
        candle.high_price = values["high_price"]
        candle.low_price = values["low_price"]
        candle.close_price = values["close_price"]
        candle.volume = values["volume"]
        candle.trade_count = values["trade_count"]


@api.get("/health", response_model=HealthResponse, responses=ERROR_RESPONSES, summary="Service health", description="Checks database connectivity and returns ingestion-aware health metadata.")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Returns service status and database connectivity.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"

        trade_count = db.query(Trade).count()

        last_trade = db.query(Trade).order_by(
            Trade.timestamp.desc()
        ).first()

        return HealthResponse(
            status="healthy",
            service="market-data-platform",
            database=db_status,
            timestamp=datetime.now(timezone.utc),
            last_trade_count=trade_count,
            last_ingestion=last_trade.timestamp if last_trade else None
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@api.get("/status/ingestion", response_model=IngestionStatusResponse, responses=ERROR_RESPONSES, summary="Ingestion status", description="Returns freshness and heartbeat telemetry for ingestion.")
async def ingestion_status(db: Session = Depends(get_db)):
    """Expose ingestion freshness and DB connectivity status."""
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as exc:
        logger.error(f"DB connectivity failed for ingestion status: {exc}")
        db_healthy = False

    last_trade = None
    if db_healthy:
        try:
            last_trade = db.query(Trade).order_by(Trade.timestamp.desc()).first()
        except Exception as exc:
            logger.error(f"Trade lookup failed for ingestion status: {exc}")
            db_healthy = False
    seconds_since_last_trade = None
    if last_trade:
        seconds_since_last_trade = (
            datetime.now(timezone.utc) - _ensure_utc(last_trade.timestamp)
        ).total_seconds()

    heartbeat_age = observability.seconds_since_last_ingestion()
    stale_threshold_seconds = settings.ingestion_interval_seconds * 3
    ingestion_alive = heartbeat_age is not None and heartbeat_age <= stale_threshold_seconds

    status = "alive" if ingestion_alive else "dead"

    return {
        "ingestion_status": status,
        "ingestion_alive": ingestion_alive,
        "stale_threshold_seconds": stale_threshold_seconds,
        "last_successful_ingestion": observability.last_successful_ingestion,
        "seconds_since_last_heartbeat": heartbeat_age,
        "seconds_since_last_trade": seconds_since_last_trade,
        "db_healthy": db_healthy,
        "uptime_seconds": round(observability.uptime_seconds(), 3),
        "process_started_at": observability.process_started_at,
    }


@api.get("/metrics", response_model=MetricsResponse, responses=ERROR_RESPONSES, summary="Runtime metrics", description="Returns service uptime, DB status, and request latency aggregates.")
async def metrics(db: Session = Depends(get_db)):
    """Runtime metrics endpoint for counts, latency, heartbeat, and DB status."""
    db_healthy = True
    db_error = None
    trade_count = None
    candle_count = None

    try:
        db.execute(text("SELECT 1"))
        trade_count = db.query(Trade).count()
        candle_count = db.query(Candle).count()
    except Exception as exc:
        db_healthy = False
        db_error = str(exc)
        logger.error(f"Metrics DB query failed: {exc}")

    heartbeat_age = observability.seconds_since_last_ingestion()
    request_metrics = observability.request_metrics()

    return {
        "service": "market-data-platform",
        "process_started_at": observability.process_started_at,
        "uptime_seconds": round(observability.uptime_seconds(), 3),
        "db": {
            "healthy": db_healthy,
            "error": db_error,
        },
        "ingestion": {
            "last_successful_write": observability.last_successful_ingestion,
            "seconds_since_last_successful_write": heartbeat_age,
            "stale_after_seconds": settings.ingestion_interval_seconds * 3,
        },
        "counts": {
            "trades": trade_count,
            "candles": candle_count,
        },
        "api_latency_ms": {
            "request_count": request_metrics.request_count,
            "average": request_metrics.average_ms,
            "max": request_metrics.max_ms,
            "last": request_metrics.last_ms,
        },
        "timestamp": datetime.now(timezone.utc),
    }


@api.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple operational dashboard that consumes API endpoints as a client."""
    return """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Market Data Platform Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }
    h1 { margin-bottom: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
    .card { border: 1px solid #d1d5db; border-radius: 8px; padding: 1rem; }
    .label { font-size: 0.85rem; color: #6b7280; margin-bottom: 0.2rem; }
    .value { font-size: 1.4rem; font-weight: 600; }
    .ok { color: #047857; }
    .bad { color: #b91c1c; }
    .small { margin-top: 1rem; color: #4b5563; }
  </style>
</head>
<body>
  <h1>Market Data Platform Dashboard</h1>
  <div class=\"grid\">
    <div class=\"card\"><div class=\"label\">Ingestion</div><div id=\"ingestion\" class=\"value\">-</div></div>
    <div class=\"card\"><div class=\"label\">Seconds Since Last Trade</div><div id=\"lastTradeSec\" class=\"value\">-</div></div>
    <div class=\"card\"><div class=\"label\">Total Trades</div><div id=\"tradeCount\" class=\"value\">-</div></div>
    <div class=\"card\"><div class=\"label\">Total Candles</div><div id=\"candleCount\" class=\"value\">-</div></div>
    <div class=\"card\"><div class=\"label\">DB Healthy</div><div id=\"dbHealthy\" class=\"value\">-</div></div>
    <div class=\"card\"><div class=\"label\">Service Uptime (s)</div><div id=\"uptime\" class=\"value\">-</div></div>
  </div>
  <div class=\"small\">Auto refreshes every 5 seconds.</div>

  <script>
    function setValue(id, value, ok) {
      const el = document.getElementById(id);
      el.textContent = value;
      el.classList.remove('ok', 'bad');
      if (ok === true) el.classList.add('ok');
      if (ok === false) el.classList.add('bad');
    }

    async function refresh() {
      try {
        const [metricsRes, statusRes] = await Promise.all([
          fetch('/metrics'),
          fetch('/status/ingestion')
        ]);

        const metrics = await metricsRes.json();
        const status = await statusRes.json();

        setValue('ingestion', status.ingestion_alive ? 'ALIVE' : 'DEAD', status.ingestion_alive);
        setValue('lastTradeSec', status.seconds_since_last_trade === null ? 'N/A' : status.seconds_since_last_trade.toFixed(1));
        setValue('tradeCount', metrics.counts.trades === null ? 'N/A' : metrics.counts.trades);
        setValue('candleCount', metrics.counts.candles === null ? 'N/A' : metrics.counts.candles);
        setValue('dbHealthy', metrics.db.healthy ? 'YES' : 'NO', metrics.db.healthy);
        setValue('uptime', metrics.uptime_seconds.toFixed(1));
      } catch (err) {
        setValue('ingestion', 'ERROR', false);
      }
    }

    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


@api.get("/symbols", response_model=SymbolsListResponse, responses=ERROR_RESPONSES, summary="List symbols", description="Returns symbols with optional pagination limits for large catalogs.")
async def get_symbols(
    limit: int = Query(
        DEFAULT_SYMBOLS_LIMIT,
        ge=1,
        le=MAX_SYMBOLS_LIMIT,
        description=f"Maximum symbols to return (1-{MAX_SYMBOLS_LIMIT})",
        examples=[100],
    ),
    db: Session = Depends(get_db),
):
    """
    Get all available symbols.
    Returns the list of symbols that have price data.
    """
    try:
        symbols = db.query(Symbol).order_by(Symbol.symbol).limit(limit).all()

        return SymbolsListResponse(
            symbols=[SymbolResponse.model_validate(s) for s in symbols],
            count=len(symbols)
        )
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/price/latest", response_model=PriceResponse, responses={**ERROR_RESPONSES, 200: {"description": "Latest trade", "content": {"application/json": {"example": {"symbol": "AAPL", "price": 185.42, "volume": 120.0, "timestamp": "2024-01-01T00:59:30Z"}}}}}, summary="Latest trade price", description="Returns the most recent trade for a symbol.")
async def get_latest_price(
    symbol: str = Query(..., min_length=1, max_length=16, pattern=SYMBOL_PATTERN, description="Symbol to query (e.g., AAPL)", examples=["AAPL"]),
    db: Session = Depends(get_db)
):
    """
    Get the latest price for a symbol.
    Returns the most recent trade data.
    """
    try:
        normalized_symbol = _validate_symbol(db, symbol)

        latest_trade = db.query(Trade).filter_by(
            symbol=normalized_symbol
        ).order_by(Trade.timestamp.desc()).first()

        if not latest_trade:
            raise HTTPException(
                status_code=404,
                detail=f"No price data available for {symbol}"
            )

        return PriceResponse(
            symbol=latest_trade.symbol,
            price=latest_trade.price,
            volume=latest_trade.volume,
            timestamp=latest_trade.timestamp
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/trades", response_model=TradesListResponse, responses={**ERROR_RESPONSES, 200: {"description": "Trades window", "content": {"application/json": {"example": {"symbol": "AAPL", "start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z", "limit": 100, "count": 2, "trades": [{"symbol": "AAPL", "price": 185.42, "volume": 120.0, "timestamp": "2024-01-01T00:59:30Z"}, {"symbol": "AAPL", "price": 185.4, "volume": 95.0, "timestamp": "2024-01-01T00:59:00Z"}]}}}}}, summary="Historical trades", description="Returns time-bounded trades for a symbol in descending timestamp order.")
async def get_trades(
    symbol: str = Query(..., min_length=1, max_length=16, pattern=SYMBOL_PATTERN, description="Symbol to query (e.g., AAPL)", examples=["AAPL"]),
    start: datetime = Query(..., description="Inclusive start timestamp (ISO-8601, timezone required)", examples=["2024-01-01T00:00:00Z"]),
    end: datetime = Query(..., description="Exclusive end timestamp (ISO-8601, timezone required)", examples=["2024-01-01T01:00:00Z"]),
    limit: int = Query(DEFAULT_TRADE_LIMIT, ge=1, le=MAX_TRADE_LIMIT, description=f"Max trades to return (1-{MAX_TRADE_LIMIT})", examples=[100]),
    db: Session = Depends(get_db),
):
    """Get trades in a time range for a symbol."""
    normalized_symbol = _validate_symbol(db, symbol)
    _validate_time_range(start, end)

    trades = (
        db.query(Trade)
        .filter(
            and_(
                Trade.symbol == normalized_symbol,
                Trade.timestamp >= start,
                Trade.timestamp < end,
            )
        )
        .order_by(Trade.timestamp.desc(), Trade.id.desc())
        .limit(limit)
        .all()
    )

    return TradesListResponse(
        symbol=normalized_symbol,
        start=start,
        end=end,
        limit=limit,
        count=len(trades),
        trades=[TradeResponse.model_validate(t) for t in trades],
    )


@api.get("/candles", response_model=CandlesListResponse, responses={**ERROR_RESPONSES, 200: {"description": "Candle window", "content": {"application/json": {"example": {"symbol": "AAPL", "interval": "1m", "start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z", "count": 1, "candles": [{"symbol": "AAPL", "interval": "1m", "timestamp": "2024-01-01T00:00:00Z", "open": 185.0, "high": 185.5, "low": 184.9, "close": 185.4, "volume": 540.0, "trade_count": 8}]}}}}}, summary="OHLCV candles", description="Returns computed OHLCV candles for a symbol and interval.")
async def get_candles(
    symbol: str = Query(..., min_length=1, max_length=16, pattern=SYMBOL_PATTERN, description="Symbol to query (e.g., AAPL)", examples=["AAPL"]),
    interval: str = Query("1m", description="Candle interval (currently supports: 1m)", examples=["1m"]),
    start: datetime = Query(..., description="Inclusive start timestamp (ISO-8601, timezone required)", examples=["2024-01-01T00:00:00Z"]),
    end: datetime = Query(..., description="Exclusive end timestamp (ISO-8601, timezone required)", examples=["2024-01-01T01:00:00Z"]),
    limit: int = Query(DEFAULT_CANDLE_LIMIT, ge=1, le=MAX_CANDLE_LIMIT, description=f"Max candles to return (1-{MAX_CANDLE_LIMIT})", examples=[500]),
    db: Session = Depends(get_db),
):
    """Get OHLCV candles in a time range for a symbol and interval."""
    normalized_symbol = _validate_symbol(db, symbol)
    _validate_time_range(start, end)
    bucket_size = _validate_interval(interval)

    # Compute on request to keep ingestion and read paths cleanly separated.
    _compute_candles_from_trades(db, normalized_symbol, interval, bucket_size, start, end)
    db.commit()

    candles = (
        db.query(Candle)
        .filter(
            and_(
                Candle.symbol == normalized_symbol,
                Candle.interval == interval,
                Candle.timestamp >= _align_to_interval(start, bucket_size),
                Candle.timestamp < end,
            )
        )
        .order_by(Candle.timestamp.asc())
        .limit(limit)
        .all()
    )

    return CandlesListResponse(
        symbol=normalized_symbol,
        interval=interval,
        start=start,
        end=end,
        count=len(candles),
        candles=[CandleResponse.model_validate(c) for c in candles],
    )


@api.get("/", response_model=RootResponse, responses=ERROR_RESPONSES, summary="API index", description="Returns high-level service and endpoint information.")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Market Data Platform",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "symbols": "/symbols",
            "latest_price": "/price/latest?symbol=AAPL",
            "trades": "/trades?symbol=AAPL&start=<ISO8601>&end=<ISO8601>&limit=100",
            "candles": "/candles?symbol=AAPL&interval=1m&start=<ISO8601>&end=<ISO8601>",
            "metrics": "/metrics",
            "ingestion_status": "/status/ingestion",
            "dashboard": "/dashboard",
        }
    }
