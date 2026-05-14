"""Tests for the rate limiter."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from rate_limiter import RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=10)
        for _ in range(3):
            allowed, retry = rl.check("1.2.3.4")
            assert allowed is True
            assert retry == 0

    def test_blocks_when_over_limit(self):
        rl = RateLimiter(max_requests=2, window_seconds=10)
        rl.check("1.2.3.4")
        rl.check("1.2.3.4")
        allowed, retry = rl.check("1.2.3.4")
        assert allowed is False
        assert retry > 0

    def test_separate_ips_separate_buckets(self):
        rl = RateLimiter(max_requests=1, window_seconds=10)
        a1, _ = rl.check("1.1.1.1")
        a2, _ = rl.check("2.2.2.2")
        assert a1 is True
        assert a2 is True
        a3, _ = rl.check("1.1.1.1")
        assert a3 is False  # second hit from same IP blocked

    def test_window_expiry(self):
        rl = RateLimiter(max_requests=1, window_seconds=1)
        rl.check("1.1.1.1")
        allowed, _ = rl.check("1.1.1.1")
        assert allowed is False
        time.sleep(1.2)
        allowed, _ = rl.check("1.1.1.1")
        assert allowed is True

    def test_stats(self):
        rl = RateLimiter(max_requests=1, window_seconds=10)
        rl.check("a")  # allowed
        rl.check("a")  # blocked
        s = rl.stats()
        assert s["allowed_attempts"] == 1
        assert s["blocked_attempts"] == 1
        assert s["tracked_ips"] == 1