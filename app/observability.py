"""In-memory observability helpers for runtime status and metrics."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Optional


@dataclass
class RequestMetricsSnapshot:
    """Snapshot of aggregate request timing metrics."""

    request_count: int
    average_ms: float
    max_ms: float
    last_ms: float


class RuntimeObservability:
    """Tracks process, ingestion heartbeat, and request latency metrics."""

    def __init__(self):
        self.process_started_at = datetime.now(timezone.utc)
        self.last_successful_ingestion: Optional[datetime] = None
        self._request_count = 0
        self._request_total_ms = 0.0
        self._request_max_ms = 0.0
        self._request_last_ms = 0.0
        self._lock = Lock()

    def mark_ingestion_success(self, timestamp: Optional[datetime] = None):
        """Mark a successful ingestion write heartbeat."""
        heartbeat = timestamp or datetime.now(timezone.utc)
        self.last_successful_ingestion = heartbeat.astimezone(timezone.utc)

    def seconds_since_last_ingestion(self) -> Optional[float]:
        """Return elapsed seconds since latest successful ingestion heartbeat."""
        if not self.last_successful_ingestion:
            return None

        now = datetime.now(timezone.utc)
        delta = now - self.last_successful_ingestion
        return max(delta.total_seconds(), 0.0)

    def mark_request_timing(self, elapsed_ms: float):
        """Record request timing in milliseconds."""
        with self._lock:
            self._request_count += 1
            self._request_total_ms += elapsed_ms
            self._request_last_ms = elapsed_ms
            if elapsed_ms > self._request_max_ms:
                self._request_max_ms = elapsed_ms

    def request_metrics(self) -> RequestMetricsSnapshot:
        """Build a metrics snapshot safe for serialization."""
        with self._lock:
            if self._request_count == 0:
                average = 0.0
            else:
                average = self._request_total_ms / self._request_count

            return RequestMetricsSnapshot(
                request_count=self._request_count,
                average_ms=round(average, 3),
                max_ms=round(self._request_max_ms, 3),
                last_ms=round(self._request_last_ms, 3),
            )

    def uptime_seconds(self) -> float:
        """Return process uptime in seconds."""
        return (datetime.now(timezone.utc) - self.process_started_at).total_seconds()


class RequestTimer:
    """Small helper for request timing."""

    def __init__(self):
        self._started = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self._started) * 1000


observability = RuntimeObservability()

