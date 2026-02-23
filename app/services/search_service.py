from app.exchanges.base import ExchangeAdapter


class SearchService:
    def __init__(self, adapter: ExchangeAdapter):
        self.adapter = adapter

    def search(self, query: str) -> list[dict]:
        return self.adapter.search(query)
