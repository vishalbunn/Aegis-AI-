"""Tests for the LRU cache."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from cache import LRUCache


class TestLRUCache:
    def test_basic_set_and_get(self):
        c = LRUCache(max_size=10, ttl_seconds=60)
        c.set("model-a", "hello", 0.3, "world")
        assert c.get("model-a", "hello", 0.3) == "world"

    def test_miss_returns_none(self):
        c = LRUCache(max_size=10, ttl_seconds=60)
        assert c.get("model-a", "no-such-prompt", 0.3) is None

    def test_different_model_different_cache(self):
        c = LRUCache(max_size=10, ttl_seconds=60)
        c.set("model-a", "hello", 0.3, "alpha")
        c.set("model-b", "hello", 0.3, "beta")
        assert c.get("model-a", "hello", 0.3) == "alpha"
        assert c.get("model-b", "hello", 0.3) == "beta"

    def test_different_temperature_different_cache(self):
        c = LRUCache(max_size=10, ttl_seconds=60)
        c.set("model-a", "hello", 0.3, "cold")
        c.set("model-a", "hello", 0.9, "hot")
        assert c.get("model-a", "hello", 0.3) == "cold"
        assert c.get("model-a", "hello", 0.9) == "hot"

    def test_ttl_expiry(self):
        c = LRUCache(max_size=10, ttl_seconds=1)
        c.set("m", "p", 0.3, "v")
        assert c.get("m", "p", 0.3) == "v"
        time.sleep(1.2)
        assert c.get("m", "p", 0.3) is None

    def test_lru_eviction(self):
        c = LRUCache(max_size=3, ttl_seconds=60)
        c.set("m", "a", 0.3, "1")
        c.set("m", "b", 0.3, "2")
        c.set("m", "c", 0.3, "3")
        # access 'a' to keep it fresh
        c.get("m", "a", 0.3)
        # add 'd', should evict 'b' (oldest unused)
        c.set("m", "d", 0.3, "4")
        assert c.get("m", "a", 0.3) == "1"
        assert c.get("m", "b", 0.3) is None  # evicted
        assert c.get("m", "c", 0.3) == "3"
        assert c.get("m", "d", 0.3) == "4"

    def test_stats(self):
        c = LRUCache(max_size=10, ttl_seconds=60)
        c.set("m", "p", 0.3, "v")
        c.get("m", "p", 0.3)  # hit
        c.get("m", "p", 0.3)  # hit
        c.get("m", "other", 0.3)  # miss
        s = c.stats()
        assert s["hits"] == 2
        assert s["misses"] == 1
        assert s["sets"] == 1
        assert s["hit_rate_pct"] > 60