from pydantic import BaseModel


class FundamentalsSchema(BaseModel):
    schema_version: str
    exchange: str
    symbol: str
    market_cap: float
    pe_ratio: float
    forward_pe: float
    eps: float
    revenue: float
    revenue_growth: float
    ebitda: float
    net_income: float
    debt_to_equity: float
    roe: float
    sector: str
    industry: str
    country: str
    currency: str
    data_source: str = "live"
    exchange_status: str = "healthy"
