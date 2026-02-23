from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Market Data Gateway"
    app_version: str = "2.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    request_timeout_seconds: int = 8
    retry_attempts: int = 3
    retry_backoff_base_seconds: float = 0.3

    schema_version: str = "1.1"

    circuit_failure_threshold: int = 5
    circuit_recovery_timeout_seconds: int = 60
    circuit_half_open_max_attempts: int = 2

    quote_ttl_seconds: int = 30
    intraday_ttl_seconds: int = 60
    historical_ttl_seconds: int = 300
    fundamentals_ttl_seconds: int = 900
    company_ttl_seconds: int = 3600

    rate_limit_requests_per_minute: int = 120

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
