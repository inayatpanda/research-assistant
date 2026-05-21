"""Phase S1 — simple in-memory per-IP rate limiter.

No external dependencies. Resets on process restart. Used to throttle
the password-auth surface (signup / login / change-password) so casual
brute-force attempts are slowed down.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class _Bucket:
    timestamps: deque[float]


class RateLimiter:
    """Sliding-window per-key counter.

    ``max_attempts`` per ``window_seconds``. Calls to :meth:`check` return
    True if the key is allowed, False if it's rate-limited.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check_and_record(self, key: str, now: float | None = None) -> bool:
        if now is None:
            now = time.monotonic()
        threshold = now - self.window_seconds
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(timestamps=deque())
                self._buckets[key] = bucket
            # Drop expired entries.
            while bucket.timestamps and bucket.timestamps[0] < threshold:
                bucket.timestamps.popleft()
            if len(bucket.timestamps) >= self.max_attempts:
                return False
            bucket.timestamps.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._buckets.clear()
            else:
                self._buckets.pop(key, None)


# Module-level singletons for the auth surface.
LOGIN_LIMITER = RateLimiter(max_attempts=10, window_seconds=300)
SIGNUP_LIMITER = RateLimiter(max_attempts=10, window_seconds=300)
