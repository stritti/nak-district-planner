"""Rate Limiter — Redis-based rate limiting with sliding window algorithm.

Provides protection against DoS attacks by limiting request rates.
Uses Redis sorted sets for efficient sliding window implementation.
"""

from __future__ import annotations

import hashlib
import logging
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
    ) -> RateLimitResult:
        """Check if a request should be rate limited.
        
        Args:
            identifier: User identifier (sub) or IP address.
            endpoint: API endpoint path.
            is_authenticated: Whether the user is authenticated.
            
        Returns:
            RateLimitResult with allowed status and rate limit information.
        """
        # Get configuration for this endpoint
        limit, window = self._get_endpoint_config(endpoint, is_authenticated)
        
        # Generate Redis key
        key = self._get_key(identifier, endpoint, window)
        
        # Get current timestamp
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window)
        
        # Use Redis sorted set to count requests in window
        # Each request is stored as a timestamp score
        timestamp_score = int(now.timestamp() * 1000)  # Milliseconds for precision
        
        try:
            # Add current request
            await self._redis.zadd(key, {str(timestamp_score): timestamp_score})
            
            # Count requests in window
            count = await self._redis.zcount(
                key,
                int(window_start.timestamp() * 1000),
                timestamp_score,
            )
            
            # Set expiration on key
            await self._redis.expire(key, window)
            
            # Check if allowed
            remaining = max(0, limit - count)
            allowed = count <= limit
            
            # Calculate reset time
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
    ) -> RateLimitResult:
        """Check burst rate limit (short window).
        
        Args:
            identifier: User identifier or IP address.
            endpoint: API endpoint path.
            
        Returns:
            RateLimitResult for burst limit check.
        """
        return await self.check_rate_limit(
            identifier=identifier,
            endpoint=endpoint,
            is_authenticated=False,  # Burst limit applies to all
        )

    def _get_endpoint_config(
        self,
        endpoint: str,
        is_authenticated: bool,
    ) -> tuple[int, int]:
        """Get rate limit configuration for an endpoint.
        
        Args:
            endpoint: API endpoint path.
            is_authenticated: Whether the user is authenticated.
            
        Returns:
            Tuple of (limit, window_seconds).
        """
        # Clean endpoint
        clean_endpoint = endpoint.split("?")[0].split("#")[0]
        
        # Check for exact match
        if clean_endpoint in self.config.endpoint_limits:
            config = self.config.endpoint_limits[clean_endpoint]
            limit = config.get("limit", self.config.default_limit)
            window = config.get("window", self.config.default_window_seconds)
        
        # Check for wildcard match
        else:
            for pattern, config in self.config.endpoint_limits.items():
                if pattern.endswith("*") and clean_endpoint.startswith(pattern[:-1]):
                    limit = config.get("limit", self.config.default_limit)
                    window = config.get("window", self.config.default_window_seconds)
                    break
            else:
                limit = self.config.default_limit
                window = self.config.default_window_seconds
        
        # Apply authenticated multiplier
        if is_authenticated:
            limit = int(limit * self.config.authenticated_multiplier)
        
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
