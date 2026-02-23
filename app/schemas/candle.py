from pydantic import BaseModel


class CandleItem(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class CandleResponseSchema(BaseModel):
    schema_version: str
    exchange: str
    symbol: str
    interval: str
    candles: list[CandleItem]
    data_source: str = "live"
    exchange_status: str = "healthy"
