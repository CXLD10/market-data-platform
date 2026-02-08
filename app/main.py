"""
Main application entry point.
Initializes the FastAPI app, database, and ingestion service.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.api import api
from app.ingestion import ingestion_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles database initialization and ingestion service lifecycle.
    """
    # Startup
    logger.info("Starting Market Data Platform...")
    
    try:
        # Initialize database schema
        init_db()
        
        # Start ingestion service in background
        ingestion_task = asyncio.create_task(ingestion_service.start())
        logger.info("Application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Market Data Platform...")
        await ingestion_service.stop()
        
        # Cancel ingestion task
        if 'ingestion_task' in locals():
            ingestion_task.cancel()
            try:
                await ingestion_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Shutdown complete")


# Create application with lifespan
api.router.lifespan_context = lifespan


def main():
    """Run the application."""
    logger.info(f"Configuration: {settings.model_dump()}")
    
    uvicorn.run(
        api,
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        lifespan="on"
    )


if __name__ == "__main__":
    main()

