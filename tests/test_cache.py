import time

from app.cache.ttl_cache import TTLCache


def test_cache_expiry():
    cache = TTLCache()
    cache.set("k", {"v": 1}, ttl_seconds=1)
    assert cache.get("k") == {"v": 1}
    time.sleep(1.1)
    assert cache.get("k") is None
