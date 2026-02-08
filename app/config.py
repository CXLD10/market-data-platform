"""
Configuration module for Market Data Platform.
All settings are loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    
    # Logging
    log_level: str = "INFO"
    
    # Ingestion
    ingestion_interval_seconds: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
