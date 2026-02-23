from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self):
        self._store: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                self._misses += 1
                return None
            if entry.expires_at <= now:
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int):
        with self._lock:
            self._store[key] = CacheEntry(value=value, expires_at=time.time() + ttl_seconds)

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return {"hits": self._hits, "misses": self._misses, "size": len(self._store)}
