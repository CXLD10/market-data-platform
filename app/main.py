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

from app.api import api
from app.config import settings
from app.database import init_db
from app.ingestion import ingestion_service

# Configure logging for stdout/stderr collectors (e.g. Cloud Run)
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles database initialization and ingestion service lifecycle.
    """
    logger.info("Starting Market Data Platform...")

    try:
        init_db()
        ingestion_task = asyncio.create_task(ingestion_service.start())
        logger.info("Application started successfully")
        yield
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down Market Data Platform...")
        await ingestion_service.stop()

        if "ingestion_task" in locals():
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
    logger.info(
        "Configuration loaded",
        extra={
            "host": settings.host,
            "port": settings.port,
            "log_level": settings.log_level,
            "ingestion_interval_seconds": settings.ingestion_interval_seconds,
            "db_pool_size": settings.db_pool_size,
            "db_max_overflow": settings.db_max_overflow,
            "db_pool_timeout_seconds": settings.db_pool_timeout_seconds,
        },
    )

    uvicorn.run(
        api,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        lifespan="on",
        access_log=True,
    )


if __name__ == "__main__":
    main()
