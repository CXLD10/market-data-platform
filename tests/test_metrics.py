from app.internal_metrics import MetricsCollector


def test_metrics_counters_increment():
    m = MetricsCollector()
    m.record_request("NSE", success=True, latency_ms=100, cache_hit=True)
    m.record_request("NSE", success=False, latency_ms=200, cache_hit=False)

    status = m.exchange_status()["NSE"]
    assert status["total_requests"] == 2
    assert status["successful_requests"] == 1
    assert status["failed_requests"] == 1
    assert status["cache_hits"] == 1
    assert status["cache_misses"] == 1
