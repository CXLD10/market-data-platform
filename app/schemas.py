"""
Pydantic schemas for API request/response validation.
Defines the contract between the API and consumers.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error payload for all API and validation errors."""

    error: str
    details: str
    status: int

    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "details": "query.symbol must match pattern ^[A-Za-z0-9._-]{1,16}$",
                "status": 422,
            }
        }


class SymbolResponse(BaseModel):
    """Response model for symbol information."""

    symbol: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class PriceResponse(BaseModel):
    """Response model for latest price information."""

    symbol: str
    price: float
    volume: float
    timestamp: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    """Response model for trade records."""

    symbol: str
    price: float
    volume: float
    timestamp: datetime

    class Config:
        from_attributes = True


class TradesListResponse(BaseModel):
    """Response model for a list of trades in a time range."""

    symbol: str
    start: datetime
    end: datetime
    limit: int
    count: int
    trades: List[TradeResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-01T01:00:00Z",
                "limit": 100,
                "count": 2,
                "trades": [
                    {"symbol": "AAPL", "price": 185.42, "volume": 120.0, "timestamp": "2024-01-01T00:59:30Z"},
                    {"symbol": "AAPL", "price": 185.4, "volume": 95.0, "timestamp": "2024-01-01T00:59:00Z"},
                ],
            }
        }


class CandleResponse(BaseModel):
    """Response model for OHLCV candle data."""

    symbol: str
    interval: str
    timestamp: datetime
    open: float = Field(alias="open_price")
    high: float = Field(alias="high_price")
    low: float = Field(alias="low_price")
    close: float = Field(alias="close_price")
    volume: float
    trade_count: int

    class Config:
        from_attributes = True
        populate_by_name = True


class CandlesListResponse(BaseModel):
    """Response model for a list of candles in a time range."""

    symbol: str
    interval: str
    start: datetime
    end: datetime
    count: int
    candles: List[CandleResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "interval": "1m",
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-01T01:00:00Z",
                "count": 1,
                "candles": [
                    {
                        "symbol": "AAPL",
                        "interval": "1m",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "open": 185.0,
                        "high": 185.5,
                        "low": 184.9,
                        "close": 185.4,
                        "volume": 540.0,
                        "trade_count": 8,
                    }
                ],
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
    service: str
    database: str
    timestamp: datetime
    last_trade_count: Optional[int] = None
    last_ingestion: Optional[datetime] = None


class SymbolsListResponse(BaseModel):
    """Response model for list of symbols."""

    symbols: List[SymbolResponse]
    count: int


class IngestionStatusResponse(BaseModel):
    """Response model for ingestion freshness endpoint."""

    ingestion_status: str
    ingestion_alive: bool
    stale_threshold_seconds: int
    last_successful_ingestion: Optional[datetime]
    seconds_since_last_heartbeat: Optional[float]
    seconds_since_last_trade: Optional[float]
    db_healthy: bool
    uptime_seconds: float
    process_started_at: datetime


class DatabaseMetrics(BaseModel):
    healthy: bool
    error: Optional[str]


class IngestionMetrics(BaseModel):
    last_successful_write: Optional[datetime]
    seconds_since_last_successful_write: Optional[float]
    stale_after_seconds: int


class CountMetrics(BaseModel):
    trades: Optional[int]
    candles: Optional[int]


class ApiLatencyMetrics(BaseModel):
    request_count: int
    average: float
    max: float
    last: float


class MetricsResponse(BaseModel):
    """Response model for runtime service metrics."""

    service: str
    process_started_at: datetime
    uptime_seconds: float
    db: DatabaseMetrics
    ingestion: IngestionMetrics
    counts: CountMetrics
    api_latency_ms: ApiLatencyMetrics
    timestamp: datetime


class RootResponseEndpoints(BaseModel):
    health: str
    symbols: str
    latest_price: str
    trades: str
    candles: str
    metrics: str
    ingestion_status: str
    dashboard: str


class RootResponse(BaseModel):
    """Response model for root endpoint metadata."""

    service: str
    version: str
    endpoints: RootResponseEndpoints
