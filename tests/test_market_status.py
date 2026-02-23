from app.utils.exchange_mapper import Exchange
from app.utils.market_status import get_market_status


def test_market_status_shape():
    data = get_market_status(Exchange.NSE)
    assert data["exchange"] == "NSE"
    assert "is_open" in data
    assert "server_time_utc" in data
    assert "local_exchange_time" in data
