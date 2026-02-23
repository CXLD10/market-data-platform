from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class ExchangeMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    latency_total_ms: float = 0.0

    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.latency_total_ms / self.total_requests


class MetricsCollector:
    def __init__(self):
        self._per_exchange: dict[str, ExchangeMetrics] = {}
        self._lock = Lock()

    def _get(self, exchange: str) -> ExchangeMetrics:
        if exchange not in self._per_exchange:
            self._per_exchange[exchange] = ExchangeMetrics()
        return self._per_exchange[exchange]

    def record_request(self, exchange: str, success: bool, latency_ms: float, cache_hit: bool):
        with self._lock:
            m = self._get(exchange)
            m.total_requests += 1
            m.latency_total_ms += max(latency_ms, 0.0)
            if success:
                m.successful_requests += 1
            else:
                m.failed_requests += 1
            if cache_hit:
                m.cache_hits += 1
            else:
                m.cache_misses += 1

    def exchange_status(self) -> dict[str, dict[str, float | int]]:
        with self._lock:
            out: dict[str, dict[str, float | int]] = {}
            for ex, m in self._per_exchange.items():
                failure_rate = 0.0 if m.total_requests == 0 else (m.failed_requests / m.total_requests)
                out[ex] = {
                    "total_requests": m.total_requests,
                    "successful_requests": m.successful_requests,
                    "failed_requests": m.failed_requests,
                    "cache_hits": m.cache_hits,
                    "cache_misses": m.cache_misses,
                    "failure_rate": round(failure_rate, 4),
                    "average_latency_ms": round(m.avg_latency_ms(), 3),
                }
            return out

    def global_metrics(self) -> dict[str, float | int | dict]:
        per = self.exchange_status()
        total_requests = sum(v["total_requests"] for v in per.values())
        total_hits = sum(v["cache_hits"] for v in per.values())
        weighted_latency = sum((v["average_latency_ms"] * v["total_requests"]) for v in per.values())
        cache_hit_rate = 0.0 if total_requests == 0 else (total_hits / total_requests)
        average_latency = 0.0 if total_requests == 0 else (weighted_latency / total_requests)
        return {
            "request_count": total_requests,
            "cache_hit_rate": round(cache_hit_rate, 4),
            "average_latency_ms": round(average_latency, 3),
            "per_exchange": per,
        }
