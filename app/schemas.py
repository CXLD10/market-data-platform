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
