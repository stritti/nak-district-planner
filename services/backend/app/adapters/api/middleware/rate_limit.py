"""Rate limiting middleware for FastAPI."""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.application.local_rate_limiter import LocalFallbackRateLimiter
from app.application.rate_limiter import (
    RateLimitConfig,
    RateLimitResult,
    increment_fail_open_counter,
    rate_limiter,
)

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply Valkey-backed limits with local fallback for sensitive endpoints."""

    def __init__(
        self,
        app,
        rate_limiter=rate_limiter,
        config: RateLimitConfig | None = None,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
        local_fallback_limiter: LocalFallbackRateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.config = config or RateLimitConfig()
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}
        self.local_fallback_limiter = local_fallback_limiter or LocalFallbackRateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.exempt_paths or request.method in self.exempt_methods:
            return await call_next(request)

        identifier = self._get_identifier(request)
        is_authenticated = self._is_authenticated(request)

        result = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            is_authenticated=is_authenticated,
            config=self.config,
            record_fail_open_metric=True,
        )
        if not result.allowed:
            return await self._rate_limited_response(request, identifier, result, "normal")

        burst_result = await self.rate_limiter.check_burst_limit(
            identifier=identifier,
            endpoint=request.url.path,
            config=self.config,
            record_fail_open_metric=False,
        )
        if burst_result.fail_open and not result.fail_open and burst_result.fail_open_reason:
            increment_fail_open_counter(burst_result.fail_open_reason)
        if not burst_result.allowed:
            return await self._rate_limited_response(request, identifier, burst_result, "burst")

        header_result = result
        if (result.fail_open or burst_result.fail_open) and self._is_sensitive_path(
            request.method,
            request.url.path,
        ):
            fallback_limit, fallback_window = self._sensitive_fallback_config(request.url.path)
            local_result = await self.local_fallback_limiter.check(
                identifier=identifier,
                endpoint=request.url.path,
                limit=fallback_limit,
                window_seconds=fallback_window,
            )
            header_result = local_result
            if not local_result.allowed:
                return await self._rate_limited_response(
                    request,
                    identifier,
                    local_result,
                    "local-fallback",
                )

        response = await call_next(request)
        for header, value in (await self.rate_limiter.get_rate_limit_headers(header_result)).items():
            response.headers[header] = value
        return response

    async def _rate_limited_response(
        self,
        request: Request,
        identifier: str,
        result: RateLimitResult,
        source: str,
    ) -> JSONResponse:
        logger.warning(
            "Rate limit exceeded for %s on %s %s (%s)",
            identifier,
            request.method,
            request.url.path,
            source,
        )
        return JSONResponse(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
            headers=await self.rate_limiter.get_rate_limit_headers(result),
        )

    @staticmethod
    def _is_sensitive_path(method: str, path: str) -> bool:
        if method.upper() != "POST":
            return False
        if path == "/api/v1/auth/oidc/token":
            return True
        if not path.startswith("/api/v1/districts/") or not path.endswith("/registrations"):
            return False
        # Public self-registration has exactly one resource id between
        # `districts` and `registrations`; admin actions append more segments.
        parts = [part for part in path.split("/") if part]
        return len(parts) == 5 and parts[:3] == ["api", "v1", "districts"]

    @staticmethod
    def _sensitive_fallback_config(path: str) -> tuple[int, int]:
        if path == "/api/v1/auth/oidc/token":
            return 30, 60
        return 10, 60

    def _get_identifier(self, request: Request) -> str:
        """Use a verified principal when available, otherwise the client IP."""
        user = getattr(request.state, "user", None)
        sub = getattr(user, "sub", None) if user else None
        if isinstance(sub, str) and sub:
            return f"user:{sub}"

        ip_address = self._get_client_ip(request)
        return f"ip:{ip_address}" if ip_address else "anonymous"

    @staticmethod
    def _is_authenticated(request: Request) -> bool:
        """Return whether a verified principal is already available.

        Middleware runs before FastAPI dependencies in the common request path,
        so mere presence of an Authorization header is not treated as proof of
        authentication. This avoids granting an authenticated rate multiplier
        to arbitrary bearer strings.
        """
        return bool(getattr(request.state, "user", None))

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        """Extract client IP according to the documented nginx trust model."""
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
            if ips:
                return ips[-1]

        if request.client:
            return request.client.host
        return None
