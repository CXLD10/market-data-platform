from pydantic import BaseModel


class CompanySchema(BaseModel):
    schema_version: str
    exchange: str
    symbol: str
    company_name: str
    sector: str
    industry: str
    description: str
    website: str
    market_cap: float
    data_source: str = "live"
    exchange_status: str = "healthy"
