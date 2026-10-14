# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

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

    def __init__(self, max_buckets: int = 4096, cleanup_every: int = 128) -> None:
        if max_buckets < 1:
            raise ValueError("max_buckets must be positive")
        if cleanup_every < 1:
            raise ValueError("cleanup_every must be positive")
        self.max_buckets = max_buckets
        self.cleanup_every = cleanup_every
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._checks_since_cleanup = 0

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
            # Denied requests are not recorded, so a bucket never exceeds `limit`.
            allowed = len(bucket) < limit
            if allowed:
                bucket.append(now)
            self._buckets[key] = bucket

            self._checks_since_cleanup += 1
            if self._checks_since_cleanup >= self.cleanup_every:
                self._evict_stale_buckets(cutoff, protected_key=key)
                self._checks_since_cleanup = 0

            # OrderedDict provides an O(1) LRU-style hard cap. The current key
            # was reinserted above and is therefore never the oldest bucket.
            while len(self._buckets) > self.max_buckets:
                self._buckets.popitem(last=False)

            count = len(bucket)
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

    def _evict_stale_buckets(self, cutoff: float, *, protected_key: str) -> None:
        """Discard stale buckets during amortized cleanup, not on every request."""
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
