from pydantic import BaseModel


class QuoteSchema(BaseModel):
    schema_version: str
    exchange: str
    symbol: str
    price: float
    open: float
    high: float
    low: float
    previous_close: float
    volume: int
    currency: str
    timestamp: str
    data_source: str = "live"
    exchange_status: str = "healthy"
