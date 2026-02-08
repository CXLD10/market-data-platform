"""
FastAPI REST API endpoints.
Provides stable interfaces for downstream consumers.
"""
from datetime import datetime, timezone, timedelta
import logging

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import text, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Symbol, Trade, Candle
from app.schemas import (
    HealthResponse,
    SymbolResponse,
    SymbolsListResponse,
    PriceResponse,
    TradeResponse,
    TradesListResponse,
    CandleResponse,
    CandlesListResponse,
)

logger = logging.getLogger(__name__)

MAX_TRADE_LIMIT = 1000
DEFAULT_TRADE_LIMIT = 100
SUPPORTED_INTERVALS = {"1m": timedelta(minutes=1)}

# Create FastAPI app
api = FastAPI(
    title="Market Data Platform",
    description="Authoritative source for financial price information",
    version="1.0.0"
)


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


@api.get("/health", response_model=HealthResponse)
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


@api.get("/symbols", response_model=SymbolsListResponse)
async def get_symbols(db: Session = Depends(get_db)):
    """
    Get all available symbols.
    Returns the list of symbols that have price data.
    """
    try:
        symbols = db.query(Symbol).order_by(Symbol.symbol).all()

        return SymbolsListResponse(
            symbols=[SymbolResponse.model_validate(s) for s in symbols],
            count=len(symbols)
        )
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/price/latest", response_model=PriceResponse)
async def get_latest_price(
    symbol: str = Query(..., description="Symbol to query (e.g., AAPL)"),
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


@api.get("/trades", response_model=TradesListResponse)
async def get_trades(
    symbol: str = Query(..., description="Symbol to query (e.g., AAPL)"),
    start: datetime = Query(..., description="Inclusive start timestamp (ISO-8601)"),
    end: datetime = Query(..., description="Exclusive end timestamp (ISO-8601)"),
    limit: int = Query(DEFAULT_TRADE_LIMIT, ge=1, le=MAX_TRADE_LIMIT, description=f"Max trades to return (1-{MAX_TRADE_LIMIT})"),
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


@api.get("/candles", response_model=CandlesListResponse)
async def get_candles(
    symbol: str = Query(..., description="Symbol to query (e.g., AAPL)"),
    interval: str = Query("1m", description="Candle interval (currently supports: 1m)"),
    start: datetime = Query(..., description="Inclusive start timestamp (ISO-8601)"),
    end: datetime = Query(..., description="Exclusive end timestamp (ISO-8601)"),
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


@api.get("/")
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
        }
    }
