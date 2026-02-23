from app.api import routes
from app.utils.exchange_mapper import Exchange


def test_cache_fallback_when_open():
    ex = Exchange.NSE
    key = "quote:NSE:INFY"
    routes.cache.set(
        key,
        {
            "price": 1.0,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "previous_close": 1.0,
            "volume": 1,
            "currency": "INR",
            "timestamp": "2024-01-01T00:00:00+00:00",
        },
        10,
    )
    for _ in range(5):
        routes.circuit_breaker.record_failure(ex.value)

    response = routes.quote(symbol="INFY", exchange="NSE")
    assert response.data_source == "cache"
    assert response.exchange_status == "degraded"
