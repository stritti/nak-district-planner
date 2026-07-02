"""Unit tests for Rate Limiter."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.rate_limiter import (
    RateLimitConfig,
    RateLimitResult,
    RateLimiter,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        
        assert config.default_limit == 200
        assert config.default_window_seconds == 60
        assert config.authenticated_multiplier == 2.0
        assert config.burst_limit == 10
        assert config.burst_window_seconds == 1
        assert config.endpoint_limits == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            default_limit=100,
            default_window_seconds=30,
            authenticated_multiplier=3.0,
            burst_limit=5,
            burst_window_seconds=2,
            endpoint_limits={"/api/test": {"limit": 50, "window": 10}},
        )
        
        assert config.default_limit == 100
        assert config.default_window_seconds == 30
        assert config.authenticated_multiplier == 3.0
        assert config.burst_limit == 5
        assert config.burst_window_seconds == 2
        assert "/api/test" in config.endpoint_limits


class TestRateLimitResult:
    """Tests for RateLimitResult dataclass."""

    def test_allowed_result(self):
        """Test result when request is allowed."""
        result = RateLimitResult(
            allowed=True,
            remaining=95,
            limit=100,
            reset_in=timedelta(seconds=30),
            retry_after=None,
        )
        
        assert result.allowed is True
        assert result.remaining == 95
        assert result.limit == 100
        assert result.reset_in == timedelta(seconds=30)
        assert result.retry_after is None

    def test_denied_result(self):
        """Test result when request is denied."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=100,
            reset_in=timedelta(seconds=60),
            retry_after=60,
        )
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 60


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis_client = AsyncMock()
        redis_client.ping = AsyncMock()
        redis_client.close = AsyncMock()
        redis_client.zadd = AsyncMock()
        redis_client.zcount = AsyncMock()
        redis_client.expire = AsyncMock()
        redis_client.zrange = AsyncMock()
        return redis_client

    @pytest.mark.asyncio
    async def test_connect(self, mock_redis):
        """Test connecting to Redis."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            limiter = RateLimiter(redis_url="redis://localhost")
            await limiter.connect()
            
            assert limiter._redis is not None
            mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close(self, mock_redis):
        """Test closing Redis connection."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            limiter = RateLimiter(redis_url="redis://localhost")
            await limiter.connect()
            await limiter.close()
            
            mock_redis.close.assert_awaited_once()
            assert limiter._redis is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_redis):
        """Test async context manager."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            limiter = RateLimiter(redis_url="redis://localhost")
            
            async with limiter:
                assert limiter._redis is not None
            
            mock_redis.close.assert_awaited_once()

    def test_get_key(self):
        """Test Redis key generation."""
        limiter = RateLimiter()
        
        key1 = limiter._get_key("user:123", "/api/test", 60)
        key2 = limiter._get_key("user:123", "/api/test", 60)
        key3 = limiter._get_key("user:456", "/api/test", 60)
        
        # Same inputs should produce same key
        assert key1 == key2
        # Different inputs should produce different keys
        assert key1 != key3
        # Keys should be SHA-256 hashes (64 hex characters)
        assert len(key1) == 64
        assert all(c in "0123456789abcdef" for c in key1)

    @pytest.mark.asyncio
    async def test_check_burst_rate_limit(self, mock_redis):
        """Test burst rate limit check."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            mock_redis.zadd.return_value = 1
            mock_redis.zcount.return_value = 1
            mock_redis.expire.return_value = True
            mock_redis.zrange.return_value = []

            config = RateLimitConfig(
                default_limit=100,
                default_window_seconds=60,
                burst_limit=10,
                burst_window_seconds=1,
            )
            limiter = RateLimiter(config=config)
            await limiter.connect()

            result = await limiter.check_burst_limit(
                identifier="user:123",
                endpoint="/api/test",
            )

            assert result.allowed is True
            assert result.limit == 10

    def test_get_endpoint_config_exact_match(self):
        """Test endpoint config with exact match."""
        config = RateLimitConfig(
            default_limit=200,
            default_window_seconds=60,
            endpoint_limits={
                "/api/test": {"limit": 100, "window": 30},
            },
        )
        
        limiter = RateLimiter(config=config)
        limit, window = limiter._get_endpoint_config("/api/test", False)
        
        assert limit == 100
        assert window == 30

    def test_get_endpoint_config_wildcard_match(self):
        """Test endpoint config with wildcard match."""
        config = RateLimitConfig(
            default_limit=200,
            default_window_seconds=60,
            endpoint_limits={
                "/api/v1/export/*": {"limit": 50, "window": 10},
            },
        )
        
        limiter = RateLimiter(config=config)
        limit, window = limiter._get_endpoint_config("/api/v1/export/123/calendar.ics", False)
        
        assert limit == 50
        assert window == 10

    def test_get_endpoint_config_default(self):
        """Test endpoint config with default values."""
        config = RateLimitConfig(
            default_limit=200,
            default_window_seconds=60,
        )
        
        limiter = RateLimiter(config=config)
        limit, window = limiter._get_endpoint_config("/api/unknown", False)
        
        assert limit == 200
        assert window == 60

    def test_get_endpoint_config_authenticated_multiplier(self):
        """Test endpoint config with authenticated multiplier."""
        config = RateLimitConfig(
            default_limit=100,
            default_window_seconds=60,
            authenticated_multiplier=3.0,
        )
        
        limiter = RateLimiter(config=config)
        
        # Unauthenticated
        limit1, _ = limiter._get_endpoint_config("/api/test", False)
        assert limit1 == 100
        
        # Authenticated
        limit2, _ = limiter._get_endpoint_config("/api/test", True)
        assert limit2 == 300  # 100 * 3.0

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, mock_redis):
        """Test rate limit check when request is allowed."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            # Mock Redis responses
            mock_redis.zadd.return_value = 1
            mock_redis.zcount.return_value = 50
            mock_redis.expire.return_value = True
            mock_redis.zrange.return_value = []
            
            limiter = RateLimiter(config=RateLimitConfig(default_limit=100))
            await limiter.connect()
            
            result = await limiter.check_rate_limit(
                identifier="user:123",
                endpoint="/api/test",
                is_authenticated=False,
            )
            
            assert result.allowed is True
            assert result.remaining == 50
            assert result.limit == 100
            assert result.retry_after is None
            
            # Verify that the reset_in is set
            assert result.reset_in is not None

    @pytest.mark.asyncio
    async def test_check_rate_limit_denied(self, mock_redis):
        """Test rate limit check when request is denied."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            # Mock Redis responses — count exceeds limit (count includes current request,
            # and count <= limit is allowed, so count must be > limit to deny)
            mock_redis.zadd.return_value = 1
            mock_redis.zcount.return_value = 101
            mock_redis.expire.return_value = True
            mock_redis.zrange.return_value = [(b"1234567890", 1234567890)]

            limiter = RateLimiter(config=RateLimitConfig(default_limit=100))
            await limiter.connect()

            result = await limiter.check_rate_limit(
                identifier="user:123",
                endpoint="/api/test",
                is_authenticated=False,
            )

            assert result.allowed is False
            assert result.remaining == max(0, 100 - 101)
            assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_get_rate_limit_headers(self, mock_redis):
        """Test rate limit header generation."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            limiter = RateLimiter()
            
            result = RateLimitResult(
                allowed=True,
                remaining=95,
                limit=100,
                reset_in=timedelta(seconds=30),
            )
            
            headers = await limiter.get_rate_limit_headers(result)
            
            assert headers["X-RateLimit-Limit"] == "100"
            assert headers["X-RateLimit-Remaining"] == "95"
            assert headers["X-RateLimit-Reset"] == "30"
            assert "Retry-After" not in headers

    @pytest.mark.asyncio
    async def test_get_rate_limit_headers_with_retry_after(self, mock_redis):
        """Test rate limit header generation with retry after."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            limiter = RateLimiter()
            
            result = RateLimitResult(
                allowed=False,
                remaining=0,
                limit=100,
                reset_in=timedelta(seconds=60),
                retry_after=60,
            )
            
            headers = await limiter.get_rate_limit_headers(result)
            
            assert headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_fail_open_on_redis_error(self, mock_redis):
        """Test that rate limiter fails open when Redis fails."""
        with patch("app.application.rate_limiter.redis.from_url", return_value=mock_redis):
            # Mock Redis to raise an error
            mock_redis.zadd.side_effect = Exception("Redis error")
            
            limiter = RateLimiter(config=RateLimitConfig(default_limit=100))
            await limiter.connect()
            
            result = await limiter.check_rate_limit(
                identifier="user:123",
                endpoint="/api/test",
                is_authenticated=False,
            )
            
            # Should fail open - allow the request
            assert result.allowed is True


class TestRateLimiterKeyGeneration:
    """Tests for Redis key generation."""

    def test_key_includes_identifier(self):
        """Test that key includes identifier."""
        limiter = RateLimiter()
        
        key1 = limiter._get_key("user:123", "/api/test", 60)
        key2 = limiter._get_key("user:456", "/api/test", 60)
        
        assert key1 != key2

    def test_key_includes_endpoint(self):
        """Test that key includes endpoint."""
        limiter = RateLimiter()
        
        key1 = limiter._get_key("user:123", "/api/test1", 60)
        key2 = limiter._get_key("user:123", "/api/test2", 60)
        
        assert key1 != key2

    def test_key_includes_window(self):
        """Test that key includes window."""
        limiter = RateLimiter()
        
        key1 = limiter._get_key("user:123", "/api/test", 60)
        key2 = limiter._get_key("user:123", "/api/test", 120)
        
        assert key1 != key2

    def test_key_normalizes_endpoint(self):
        """Test that endpoint is normalized (query params removed)."""
        limiter = RateLimiter()
        
        key1 = limiter._get_key("user:123", "/api/test?param=1", 60)
        key2 = limiter._get_key("user:123", "/api/test?param=2", 60)
        
        # Query parameters should be ignored
        assert key1 == key2
