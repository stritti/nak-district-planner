"""Rate Limiting Middleware for FastAPI.

This middleware implements rate limiting using Redis-based sliding window algorithm.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.application.rate_limiter import RateLimitConfig, rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for rate limiting.
    
    Registered via ``app.add_middleware()`` — Starlette instantiates it
    as ASGI middleware and calls ``dispatch(request, call_next)`` for
    each request.

    This middleware:
    - Checks rate limits for each request
    - Returns HTTP 429 when rate limit is exceeded
    - Adds standard rate limit headers to responses
    - Supports both authenticated and unauthenticated users
    """

    def __init__(
        self,
        app,
        rate_limiter=rate_limiter,
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
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.config = config or RateLimitConfig()
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}

    async def dispatch(
        self,
        request: Request,
        call_next,
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
            return await call_next(request)
        
        # Skip rate limiting for exempt methods
        if request.method in self.exempt_methods:
            return await call_next(request)
        
        # Get identifier (user sub or IP address)
        identifier = self._get_identifier(request)
        
        # Check if user is authenticated
        is_authenticated = self._is_authenticated(request)
        
        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            is_authenticated=is_authenticated,
            config=self.config,
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

        Since middleware runs before FastAPI dependencies (get_current_user),
        ``request.state.user`` may not be populated yet. As a fallback this
        method extracts the ``sub`` claim directly from the Bearer JWT payload
        without verifying the signature — safe because the value is used only
        for rate-limit grouping, not authentication. Full token verification
        happens later in the route dependency.

        Args:
            request: HTTP request.

        Returns:
            Identifier string.
        """
        # Try to get user sub from authenticated user (populated after deps run)
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            if hasattr(user, "sub") and user.sub:
                return f"user:{user.sub}"

        # Fallback: extract sub from Bearer JWT payload without verification
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            import base64
            import json

            try:
                # JWT: header.payload.signature — decode payload segment
                payload_b64 = token.split(".")[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                if "sub" in payload:
                    return f"user:{payload['sub']}"
            except (IndexError, ValueError, json.JSONDecodeError):
                pass

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
        
        Trust model: behind nginx reverse proxy. The proxy sets
        ``X-Real-IP`` to ``$remote_addr``. If that header is absent,
        takes the last entry from ``X-Forwarded-For`` (the proxy-appended
        value), which is not spoofable by external clients because ``nginx``
        appends ``$remote_addr`` to any incoming header via
        ``$proxy_add_x_forwarded_for``.
        
        Args:
            request: HTTP request.
            
        Returns:
            Client IP address, or None if not available.
        """
        # 1. X-Real-IP — set by nginx to $remote_addr, not alterable by client
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 2. X-Forwarded-For — last entry is the proxy-appended $remote_addr
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
            if ips:
                return ips[-1]
        
        # 3. Fall back to direct client address
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
