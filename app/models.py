"""
Database models for Market Data Platform.
Defines the schema for symbols and trades.
"""
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Symbol(Base):
    """Represents a tradeable symbol (e.g., AAPL, GOOGL)."""
    __tablename__ = "symbols"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Symbol(symbol={self.symbol}, name={self.name})>"


class Trade(Base):
    """Represents a single trade event."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), ForeignKey("symbols.symbol"), nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Composite index for efficient queries by symbol and time
    __table_args__ = (
        Index('ix_trades_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<Trade(symbol={self.symbol}, price={self.price}, timestamp={self.timestamp})>"


class Candle(Base):
    """Represents aggregated OHLCV candlestick data for a symbol and interval."""
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), ForeignKey("symbols.symbol"), nullable=False, index=True)
    interval = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    trade_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_candles_symbol_timestamp', 'symbol', 'timestamp'),
        Index('ux_candles_symbol_interval_timestamp', 'symbol', 'interval', 'timestamp', unique=True),
    )

    def __repr__(self):
        return (
            f"<Candle(symbol={self.symbol}, interval={self.interval}, "
            f"timestamp={self.timestamp})>"
        )
