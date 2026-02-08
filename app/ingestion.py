"""
Data ingestion service.
Generates synthetic trades and persists them to the database.
"""
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import List

from app.database import get_db_session
from app.models import Symbol, Trade
from app.config import settings
from app.observability import observability

logger = logging.getLogger(__name__)


class IngestionService:
    """Handles periodic ingestion of synthetic market data."""
    
    # Default symbols to track
    DEFAULT_SYMBOLS = [
        ("AAPL", "Apple Inc."),
        ("GOOGL", "Alphabet Inc."),
        ("MSFT", "Microsoft Corporation"),
        ("TSLA", "Tesla Inc."),
        ("AMZN", "Amazon.com Inc."),
    ]
    
    def __init__(self):
        self.running = False
        self.last_prices = {}  # Track last price for random walk
        
    async def initialize_symbols(self):
        """Ensure default symbols exist in the database."""
        logger.info("Initializing symbols...")
        
        with get_db_session() as session:
            for symbol_code, name in self.DEFAULT_SYMBOLS:
                # Check if symbol already exists
                existing = session.query(Symbol).filter_by(symbol=symbol_code).first()
                if not existing:
                    symbol = Symbol(symbol=symbol_code, name=name)
                    session.add(symbol)
                    # Initialize random starting price
                    self.last_prices[symbol_code] = random.uniform(100, 500)
                    logger.info(f"Created symbol: {symbol_code}")
                else:
                    # Get last known price if exists
                    last_trade = session.query(Trade).filter_by(
                        symbol=symbol_code
                    ).order_by(Trade.timestamp.desc()).first()
                    
                    if last_trade:
                        self.last_prices[symbol_code] = last_trade.price
                    else:
                        self.last_prices[symbol_code] = random.uniform(100, 500)
            
            session.commit()
        
        logger.info(f"Initialized {len(self.DEFAULT_SYMBOLS)} symbols")
    
    def generate_price_movement(self, current_price: float) -> float:
        """
        Generate realistic price movement using random walk.
        Typical price changes between -2% and +2%.
        """
        percent_change = random.uniform(-0.02, 0.02)
        new_price = current_price * (1 + percent_change)
        return round(new_price, 2)
    
    def generate_volume(self) -> float:
        """Generate random trading volume."""
        return round(random.uniform(1000, 100000), 2)
    
    async def generate_trades(self):
        """Generate synthetic trades for all symbols."""
        timestamp = datetime.now(timezone.utc)
        trades_created = 0
        
        with get_db_session() as session:
            for symbol_code in self.last_prices.keys():
                # Update price with random walk
                current_price = self.last_prices[symbol_code]
                new_price = self.generate_price_movement(current_price)
                self.last_prices[symbol_code] = new_price
                
                # Create trade record
                trade = Trade(
                    symbol=symbol_code,
                    price=new_price,
                    volume=self.generate_volume(),
                    timestamp=timestamp
                )
                session.add(trade)
                trades_created += 1
            
            session.commit()
        
        logger.info(
            f"Generated {trades_created} trades at {timestamp.isoformat()}"
        )
        observability.mark_ingestion_success(timestamp)
        return trades_created
    
    async def start(self):
        """Start the ingestion loop."""
        self.running = True
        logger.info(
            f"Starting ingestion service (interval: {settings.ingestion_interval_seconds}s)"
        )
        
        # Initialize symbols on startup
        await self.initialize_symbols()
        
        # Main ingestion loop
        while self.running:
            try:
                await self.generate_trades()
                await asyncio.sleep(settings.ingestion_interval_seconds)
            except Exception as e:
                logger.error(f"Error in ingestion loop: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(settings.ingestion_interval_seconds)
    
    async def stop(self):
        """Stop the ingestion loop."""
        logger.info("Stopping ingestion service...")
        self.running = False


# Global ingestion service instance
ingestion_service = IngestionService()
