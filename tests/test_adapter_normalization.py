from app.exchanges.yahoo_adapter import YahooAdapter
from app.utils.exchange_mapper import Exchange


def test_candle_sorted_and_native(monkeypatch):
    adapter = YahooAdapter()

    def fake_fetch_chart(provider_symbol, interval, range_value):
        return {
            "timestamp": [1704067500, 1704067200],
            "indicators": {
                "quote": [
                    {
                        "open": [2, 1],
                        "high": [2.1, 1.1],
                        "low": [1.9, 0.9],
                        "close": [2.05, 1.05],
                        "volume": [120, 100],
                    }
                ]
            },
        }

    monkeypatch.setattr(adapter, "_fetch_chart", fake_fetch_chart)
    candles = adapter.fetch_candles("AAPL", Exchange.NASDAQ, "5m", "1d")
    assert candles[0]["timestamp"] < candles[1]["timestamp"]
    assert isinstance(candles[0]["open"], float)
    assert isinstance(candles[0]["volume"], int)
