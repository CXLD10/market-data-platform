import time

from app.resilience_circuit_breaker import CircuitState, ExchangeCircuitBreaker


def test_circuit_transitions_open_half_open_closed():
    cb = ExchangeCircuitBreaker(failure_threshold=2, recovery_timeout_seconds=1, half_open_max_attempts=2)
    ex = "NSE"

    assert cb.can_execute(ex) is True
    cb.record_failure(ex)
    cb.record_failure(ex)
    assert cb.state(ex) == CircuitState.OPEN
    assert cb.can_execute(ex) is False

    time.sleep(1.1)
    assert cb.can_execute(ex) is True
    assert cb.state(ex) == CircuitState.HALF_OPEN

    cb.record_success(ex)
    assert cb.state(ex) == CircuitState.CLOSED
