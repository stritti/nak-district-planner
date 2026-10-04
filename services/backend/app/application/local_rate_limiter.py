"""Bounded in-process fallback rate limiter for security-sensitive endpoints.

The primary limiter remains Valkey-backed and horizontally consistent. This
fallback is intentionally narrower: it is used only when the primary limiter
fails open, so a cache outage does not also remove all abuse protection from
public authentication and self-registration endpoints.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict, deque
from datetime import timedelta

from app.application.rate_limiter import RateLimitResult


class LocalFallbackRateLimiter:
    """Small process-local sliding-window limiter with bounded memory."""

    def __init__(self, max_buckets: int = 4096) -> None:
        if max_buckets < 1:
            raise ValueError("max_buckets must be positive")
        self.max_buckets = max_buckets
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def check(
        self,
        *,
        identifier: str,
        endpoint: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Record one request and return its local sliding-window result."""
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")

        now = time.monotonic()
        cutoff = now - window_seconds
        key = f"{identifier}:{endpoint}"

        async with self._lock:
            bucket = self._buckets.pop(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            bucket.append(now)
            self._buckets[key] = bucket

            self._evict_empty_or_old_buckets(cutoff, protected_key=key)
            while len(self._buckets) > self.max_buckets:
                oldest_key, _ = self._buckets.popitem(last=False)
                if oldest_key == key:
                    self._buckets[oldest_key] = bucket
                    break

            count = len(bucket)
            allowed = count <= limit
            oldest = bucket[0]
            reset_seconds = max(0.0, oldest + window_seconds - now)
            retry_after = max(1, int(reset_seconds)) if not allowed else None

            return RateLimitResult(
                allowed=allowed,
                remaining=max(0, limit - count),
                limit=limit,
                reset_in=timedelta(seconds=reset_seconds),
                retry_after=retry_after,
            )

    def _evict_empty_or_old_buckets(self, cutoff: float, *, protected_key: str) -> None:
        """Discard stale buckets before applying the hard bucket cap."""
        stale_keys: list[str] = []
        for key, bucket in self._buckets.items():
            if key == protected_key:
                continue
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                stale_keys.append(key)
        for key in stale_keys:
            self._buckets.pop(key, None)
