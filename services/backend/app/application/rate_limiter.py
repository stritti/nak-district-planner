"""Rate Limiter — Redis-based rate limiting with sliding window algorithm.

Provides protection against DoS attacks by limiting request rates.
Uses Redis sorted sets for efficient sliding window implementation.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Default limits
    default_limit: int = 200
    default_window_seconds: int = 60

    # Endpoint-specific limits
    endpoint_limits: dict[str, dict[str, Any]] = None

    # Authenticated vs unauthenticated users
    authenticated_multiplier: float = 2.0

    # Burst protection
    burst_limit: int = 10
    burst_window_seconds: int = 1

    def __post_init__(self):
        if self.endpoint_limits is None:
            self.endpoint_limits = {}


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    limit: int
    reset_in: timedelta
    retry_after: int | None = None


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm.
    
    Uses Redis sorted sets to efficiently count requests in sliding windows.
    Each request is stored as a timestamp in a sorted set, and the count
    of requests in the window is obtained by counting elements within the
    timestamp range.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        config: RateLimitConfig | None = None,
    ):
        """Initialize the rate limiter.
        
        Args:
            redis_url: Redis connection URL. If None, uses settings.redis_url.
            config: Rate limit configuration. If None, uses default config.
        """
        self.redis_url = redis_url or settings.redis_url
        self.config = config or RateLimitConfig()
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        
        # Test connection
        try:
            await self._redis.ping()
            logger.info("Connected to Redis for rate limiting")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _get_key(self, identifier: str, endpoint: str, window: int) -> str:
        """Generate Redis key for rate limiting.
        
        Args:
            identifier: User identifier or IP address.
            endpoint: API endpoint path.
            window: Window size in seconds.
            
        Returns:
            Redis key string.
        """
        # Normalize endpoint (remove query parameters, etc.)
        clean_endpoint = endpoint.split("?")[0].split("#")[0]
        
        # Create a hash of the identifier + endpoint to keep keys short
        key_data = f"rate_limit:{window}:{identifier}:{clean_endpoint}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        is_authenticated: bool = False,
        config: RateLimitConfig | None = None,
    ) -> RateLimitResult:
        """Check if a request should be rate limited.
        
        Args:
            identifier: User identifier (sub) or IP address.
            endpoint: API endpoint path.
            is_authenticated: Whether the user is authenticated.
            config: Optional override config. If None, uses self.config.
            
        Returns:
            RateLimitResult with allowed status and rate limit information.
        """
        # Get configuration for this endpoint (use override config if provided)
        limit, window = self._get_endpoint_config(endpoint, is_authenticated, config)
        
        # Generate Redis key
        key = self._get_key(identifier, endpoint, window)
        
        # Get current timestamp
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window)
        
        # Use Redis sorted set to count requests in window
        # Each request is stored as a timestamp score
        timestamp_score = int(now.timestamp() * 1000)  # Milliseconds for precision
        
        try:
            # Prune entries older than the window before adding the new one
            await self._redis.zremrangebyscore(
                key,
                0,
                int(window_start.timestamp() * 1000),
            )
            
            # Add current request — member includes a nonce so requests
            # arriving in the same millisecond each produce a unique member
            # (otherwise ZADD silently overwrites same-key entries).
            nonce = uuid.uuid4().hex[:8]
            await self._redis.zadd(key, {f"{timestamp_score}:{nonce}": timestamp_score})
            
            # Count requests in window (includes the one we just added)
            count = await self._redis.zcount(
                key,
                int(window_start.timestamp() * 1000),
                timestamp_score,
            )
            
            # Set expiration on key
            await self._redis.expire(key, window)
            
            # Check if allowed
            # count already includes the current request, so count == limit
            # represents the last request that should be allowed.
            remaining = max(0, limit - count)
            allowed = count <= limit
            
            # Calculate reset time
            # Get the oldest request to determine when the window will slide
            oldest_timestamp = await self._redis.zrange(key, 0, 0, withscores=True)
            if oldest_timestamp:
                oldest_score = int(oldest_timestamp[0][1])
                oldest_time = datetime.fromtimestamp(oldest_score / 1000, UTC)
                reset_in = oldest_time + timedelta(seconds=window) - now
            else:
                reset_in = timedelta(seconds=window)
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                limit=limit,
                reset_in=reset_in,
                retry_after=int(reset_in.total_seconds()) if not allowed else None,
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return RateLimitResult(
                allowed=True,
                remaining=limit,
                limit=limit,
                reset_in=timedelta(seconds=window),
            )

    async def check_burst_limit(
        self,
        identifier: str,
        endpoint: str,
        config: RateLimitConfig | None = None,
    ) -> RateLimitResult:
        """Check burst rate limit (short-window spike protection).
        
        Uses ``burst_limit`` and ``burst_window_seconds`` from the config
        (defaults to 10 requests per 1 second).
        
        Args:
            identifier: User identifier or IP address.
            endpoint: API endpoint path.
            config: Optional override config. Falls back to self.config.
            
        Returns:
            RateLimitResult for burst limit check.
        """
        cfg = config or self.config
        burst_endpoint = f"{endpoint}__burst__"
        return await self.check_rate_limit(
            identifier=identifier,
            endpoint=burst_endpoint,
            is_authenticated=False,  # Burst limit applies to all
            config=RateLimitConfig(
                default_limit=cfg.burst_limit,
                default_window_seconds=cfg.burst_window_seconds,
                authenticated_multiplier=1.0,
            ),
        )

    def _get_endpoint_config(
        self,
        endpoint: str,
        is_authenticated: bool,
        config: RateLimitConfig | None = None,
    ) -> tuple[int, int]:
        """Get rate limit configuration for an endpoint.
        
        Args:
            endpoint: API endpoint path.
            is_authenticated: Whether the user is authenticated.
            config: Optional override config. Falls back to self.config.
            
        Returns:
            Tuple of (limit, window_seconds).
        """
        # Use override config if provided, otherwise self.config
        cfg = config or self.config
        
        # Clean endpoint
        clean_endpoint = endpoint.split("?")[0].split("#")[0]
        
        # Check for exact match
        if clean_endpoint in cfg.endpoint_limits:
            ep_config = cfg.endpoint_limits[clean_endpoint]
            limit = ep_config.get("limit", cfg.default_limit)
            window = ep_config.get("window", cfg.default_window_seconds)
        
        # Check for wildcard match
        else:
            for pattern, ep_config in cfg.endpoint_limits.items():
                if pattern.endswith("*") and clean_endpoint.startswith(pattern[:-1]):
                    limit = ep_config.get("limit", cfg.default_limit)
                    window = ep_config.get("window", cfg.default_window_seconds)
                    break
            else:
                limit = cfg.default_limit
                window = cfg.default_window_seconds
        
        # Apply authenticated multiplier
        if is_authenticated:
            limit = int(limit * cfg.authenticated_multiplier)
        
        return limit, window

    async def get_rate_limit_headers(
        self,
        result: RateLimitResult,
    ) -> dict[str, str]:
        """Get standard rate limit headers for response.
        
        Args:
            result: Rate limit check result.
            
        Returns:
            Dictionary of rate limit headers.
        """
        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_in.total_seconds())),
        }
        
        if result.retry_after is not None:
            headers["Retry-After"] = str(result.retry_after)
        
        return headers


# Global rate limiter instance
rate_limiter = RateLimiter()
