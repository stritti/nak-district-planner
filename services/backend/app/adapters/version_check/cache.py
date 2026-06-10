"""In-memory cache with TTL for version check results."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CachedValue:
    """A cached value with expiration."""

    value: str | None
    expires_at: float  # Unix timestamp


class VersionCache:
    """Simple in-memory TTL cache for version check results.

    Uses the same pattern as OIDC JWKS/discovery caching in the project.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._latest_version: CachedValue | None = None
        self._last_checked: float | None = None

    @property
    def ttl(self) -> int:
        return self._ttl

    def get(self) -> str | None:
        """Return cached latest version if still fresh, else None."""
        if self._latest_version is None:
            return None
        if time.time() > self._latest_version.expires_at:
            return None
        return self._latest_version.value

    def set(self, version: str | None) -> None:
        """Store a version with TTL."""
        self._latest_version = CachedValue(
            value=version,
            expires_at=time.time() + self._ttl,
        )
        self._last_checked = time.time()

    @property
    def last_checked(self) -> float | None:
        return self._last_checked

    def clear(self) -> None:
        self._latest_version = None
        self._last_checked = None


# Singleton cache instance (same pattern as OIDC adapter caching)
version_cache = VersionCache(ttl_seconds=3600)
