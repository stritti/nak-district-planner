"""Rate Limiting Middleware for FastAPI.

This middleware implements rate limiting using Redis-based sliding window algorithm.
"""

import logging
from typing import Callable, Awaitable

from fastapi import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.application.rate_limiter import RateLimitConfig, RateLimitResult, rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """FastAPI Middleware for rate limiting.
    
    This middleware:
    - Checks rate limits for each request
    - Returns HTTP 429 when rate limit is exceeded
    - Adds standard rate limit headers to responses
    - Supports both authenticated and unauthenticated users
    """

    def __init__(
        self,
        app,
        rate_limiter: rate_limiter = rate_limiter,
        config: RateLimitConfig | None = None,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ):
        """Initialize the rate limit middleware.
        
        Args:
            app: FastAPI application instance.
            rate_limiter: Rate limiter instance.
            config: Rate limit configuration.
            exempt_paths: Set of paths to exempt from rate limiting.
            exempt_methods: Set of HTTP methods to exempt.
        """
        self.app = app
        self.rate_limiter = rate_limiter
        self.config = config or RateLimitConfig()
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process a request through the middleware.
        
        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.
            
        Returns:
            HTTP response, potentially with rate limit headers.
        """
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            response = await call_next(request)
            return response
        
        # Skip rate limiting for exempt methods
        if request.method in self.exempt_methods:
            response = await call_next(request)
            return response
        
        # Get identifier (user sub or IP address)
        identifier = self._get_identifier(request)
        
        # Check if user is authenticated
        is_authenticated = self._is_authenticated(request)
        
        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            is_authenticated=is_authenticated,
        )
        
        # If rate limit exceeded, return 429
        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier} on {request.method} {request.url.path}"
            )
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers=await self.rate_limiter.get_rate_limit_headers(result),
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        rate_limit_headers = await self.rate_limiter.get_rate_limit_headers(result)
        for header, value in rate_limit_headers.items():
            response.headers[header] = value
        
        return response

    def _get_identifier(self, request: Request) -> str:
        """Get identifier for rate limiting (user sub or IP address).
        
        Args:
            request: HTTP request.
            
        Returns:
            Identifier string.
        """
        # Try to get user sub from authenticated user
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            if hasattr(user, "sub") and user.sub:
                return f"user:{user.sub}"
        
        # Fall back to IP address
        ip_address = self._get_client_ip(request)
        if ip_address:
            return f"ip:{ip_address}"
        
        # Last resort - use a generic identifier
        return "anonymous"

    def _is_authenticated(self, request: Request) -> bool:
        """Check if request is authenticated.
        
        Args:
            request: HTTP request.
            
        Returns:
            True if user is authenticated.
        """
        if hasattr(request.state, "user") and request.state.user:
            return True
        
        # Check for Bearer token
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return True
        
        return False

    def _get_client_ip(self, request: Request) -> str | None:
        """Extract client IP address from request.
        
        Args:
            request: HTTP request.
            
        Returns:
            Client IP address, or None if not available.
        """
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client address
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
