"""
Per-IP sliding-window rate limiter.

Why: a single user (or a bot scraping your demo) can easily blow through
your daily LLM budget. Without this, the project is one Reddit link away
from being unusable.

Design:
- Sliding window: max N requests per IP in the last W seconds.
- In-memory only. For multi-worker deployments, swap in Redis later.
- Defaults tuned for free-tier hosting: 10 requests / 10 minutes per IP.
- The eval pipeline doesn't go through this — it calls the function directly.
"""
import time
import threading
from collections import deque


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 600):
        self._max = max_requests
        self._window = window_seconds
        self._lock = threading.Lock()
        self._ips: dict = {}  # ip -> deque of timestamps
        self._blocked_attempts = 0
        self._allowed_attempts = 0

    def check(self, ip: str) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds).
        allowed = True if request is permitted, False if rate-limited."""
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            q = self._ips.setdefault(ip, deque())
            # drop expired timestamps
            while q and q[0] < cutoff:
                q.popleft()

            if len(q) >= self._max:
                self._blocked_attempts += 1
                # retry-after = when the oldest request will expire
                retry_after = int(self._window - (now - q[0])) + 1
                return False, max(retry_after, 1)

            q.append(now)
            self._allowed_attempts += 1
            return True, 0

    def stats(self) -> dict:
        with self._lock:
            total = self._allowed_attempts + self._blocked_attempts
            block_rate = round(100 * self._blocked_attempts / total, 2) if total else 0.0
            return {
                "max_requests": self._max,
                "window_seconds": self._window,
                "tracked_ips": len(self._ips),
                "allowed_attempts": self._allowed_attempts,
                "blocked_attempts": self._blocked_attempts,
                "block_rate_pct": block_rate,
            }


# Singleton
rate_limiter = RateLimiter(max_requests=10, window_seconds=600)