"""
Simple in-memory cache for LLM calls.

Why: same prompt → same answer (with low temperature). Caching cuts cost,
improves latency on demo traffic, and protects free-tier API budgets.

Design choices:
- TTL: 1 hour (decisions can stay fresh, but stale entries auto-evict).
- Max size: 1000 entries (LRU eviction).
- Keyed on (model, prompt, temperature).
- Thread-safe via lock — uvicorn workers may share this in single-process mode.
- Stats exposed for the /admin/stats endpoint.
"""
import time
import hashlib
import threading
from collections import OrderedDict
from typing import Optional


class LRUCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._store: "OrderedDict[str, tuple[float, str]]" = OrderedDict()
        self._max = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._sets = 0

    @staticmethod
    def _key(model: str, prompt: str, temperature: float) -> str:
        h = hashlib.sha256(f"{model}|{temperature:.2f}|{prompt}".encode()).hexdigest()
        return h

    def get(self, model: str, prompt: str, temperature: float) -> Optional[str]:
        k = self._key(model, prompt, temperature)
        with self._lock:
            entry = self._store.get(k)
            if entry is None:
                self._misses += 1
                return None
            ts, val = entry
            if time.time() - ts > self._ttl:
                # expired
                del self._store[k]
                self._misses += 1
                return None
            # mark as recently used
            self._store.move_to_end(k)
            self._hits += 1
            return val

    def set(self, model: str, prompt: str, temperature: float, value: str) -> None:
        k = self._key(model, prompt, temperature)
        with self._lock:
            if k in self._store:
                self._store.move_to_end(k)
            self._store[k] = (time.time(), value)
            self._sets += 1
            while len(self._store) > self._max:
                self._store.popitem(last=False)  # evict oldest

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = round(100 * self._hits / total, 2) if total else 0.0
            return {
                "size": len(self._store),
                "max_size": self._max,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "sets": self._sets,
                "hit_rate_pct": hit_rate,
            }

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0
            self._sets = 0


# Singleton — one shared cache per process.
llm_cache = LRUCache(max_size=1000, ttl_seconds=3600)