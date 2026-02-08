"""
Pydantic schemas for API request/response validation.
Defines the contract between the API and consumers.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


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
