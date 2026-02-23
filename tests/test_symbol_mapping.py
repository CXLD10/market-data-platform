from app.utils.exchange_mapper import Exchange, from_provider_symbol, to_provider_symbol


def test_to_provider_symbol():
    assert to_provider_symbol("INFY", Exchange.NSE) == "INFY.NS"
    assert to_provider_symbol("INFY", Exchange.BSE) == "INFY.BO"
    assert to_provider_symbol("AAPL", Exchange.NASDAQ) == "AAPL"


def test_from_provider_symbol():
    assert from_provider_symbol("INFY.NS") == ("INFY", Exchange.NSE)
    assert from_provider_symbol("TCS.BO") == ("TCS", Exchange.BSE)
    assert from_provider_symbol("MSFT") == ("MSFT", Exchange.NASDAQ)
