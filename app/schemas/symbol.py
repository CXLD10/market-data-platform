from pydantic import BaseModel


class SearchResultSchema(BaseModel):
    schema_version: str
    symbol: str
    exchange: str
    company_name: str
    sector: str
    currency: str
