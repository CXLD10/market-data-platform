from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitStatus:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_timestamp: float | None = None
    half_open_attempts: int = 0


class ExchangeCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_max_attempts: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_attempts = half_open_max_attempts
        self._state: dict[str, CircuitStatus] = {}
        self._lock = Lock()

    def _get(self, exchange: str) -> CircuitStatus:
        if exchange not in self._state:
            self._state[exchange] = CircuitStatus()
        return self._state[exchange]

    def can_execute(self, exchange: str) -> bool:
        now = time.time()
        with self._lock:
            status = self._get(exchange)
            if status.state == CircuitState.CLOSED:
                return True

            if status.state == CircuitState.OPEN:
                if status.last_failure_timestamp and (now - status.last_failure_timestamp) >= self.recovery_timeout_seconds:
                    status.state = CircuitState.HALF_OPEN
                    status.half_open_attempts = 0
                    return True
                return False

            if status.state == CircuitState.HALF_OPEN:
                if status.half_open_attempts < self.half_open_max_attempts:
                    status.half_open_attempts += 1
                    return True
                return False

            return False

    def record_success(self, exchange: str):
        with self._lock:
            status = self._get(exchange)
            status.success_count += 1
            status.failure_count = 0
            status.half_open_attempts = 0
            status.state = CircuitState.CLOSED

    def record_failure(self, exchange: str):
        with self._lock:
            status = self._get(exchange)
            status.failure_count += 1
            status.last_failure_timestamp = time.time()

            if status.state == CircuitState.HALF_OPEN:
                status.state = CircuitState.OPEN
                status.half_open_attempts = 0
                return

            if status.failure_count >= self.failure_threshold:
                status.state = CircuitState.OPEN

    def state(self, exchange: str) -> CircuitState:
        with self._lock:
            return self._get(exchange).state

    def snapshot(self) -> dict[str, dict[str, int | float | str | None]]:
        with self._lock:
            output = {}
            for exchange, status in self._state.items():
                output[exchange] = {
                    "state": status.state.value,
                    "failure_count": status.failure_count,
                    "success_count": status.success_count,
                    "last_failure_timestamp": status.last_failure_timestamp,
                }
            return output
