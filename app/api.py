"""
FastAPI REST API endpoints.
Provides stable interfaces for downstream consumers.
"""
from sqlalchemy import text
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import logging

from app.database import get_db
from app.models import Symbol, Trade
from app.schemas import (
    HealthResponse,
    SymbolResponse,
    SymbolsListResponse,
    PriceResponse
)

logger = logging.getLogger(__name__)

# Create FastAPI app
api = FastAPI(
    title="Market Data Platform",
    description="Authoritative source for financial price information",
    version="1.0.0"
)

@api.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Returns service status and database connectivity.
    """
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        
        # Get latest trade count
        trade_count = db.query(Trade).count()
        
        # Get last ingestion time
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
        # Validate symbol exists
        symbol_obj = db.query(Symbol).filter_by(symbol=symbol.upper()).first()
        if not symbol_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found"
            )
        
        # Get latest trade
        latest_trade = db.query(Trade).filter_by(
            symbol=symbol.upper()
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


@api.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Market Data Platform",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "symbols": "/symbols",
            "latest_price": "/price/latest?symbol=AAPL"
        }
    }
