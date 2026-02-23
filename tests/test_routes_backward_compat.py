from app.api import routes


def test_health_payload():
    payload = routes.health()
    assert payload["status"] == "ok"
    assert payload["schema_version"] == "1.1"


def test_backward_route_and_schema_version():
    payload = routes.symbols()
    assert "symbols" in payload
    assert "count" in payload
    assert payload["schema_version"] == "1.1"


def test_exchange_status_endpoint_shape():
    payload = routes.exchanges_status()
    assert payload["schema_version"] == "1.1"
    assert "NSE" in payload
    assert "state" in payload["NSE"]
