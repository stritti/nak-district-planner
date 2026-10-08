"""Rate limiting middleware for FastAPI."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.adapters.api.client_ip import get_client_ip
from app.application.local_rate_limiter import LocalFallbackRateLimiter
from app.application.rate_limiter import (
    RateLimitConfig,
    RateLimitResult,
    increment_fail_open_counter,
    rate_limiter,
)

logger = logging.getLogger(__name__)

_UUID_SEGMENT = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


@dataclass(frozen=True)
class SensitiveFallbackConfig:
    """Local fallback limits used only while the shared Valkey limiter is unavailable."""

    auth_token_limit: int = 30
    public_registration_limit: int = 10
    window_seconds: int = 60


@dataclass(frozen=True)
class SensitiveEndpointRule:
    """Declarative description of a route that needs a local fail-open fallback."""

    method: str
    pattern: re.Pattern[str]
    limit_attribute: str

    def matches(self, method: str, path: str) -> bool:
        return method.upper() == self.method and self.pattern.fullmatch(path) is not None


SENSITIVE_ENDPOINT_RULES = (
    SensitiveEndpointRule(
        method="POST",
        pattern=re.compile(r"/api/v1/auth/oidc/token"),
        limit_attribute="auth_token_limit",
    ),
    SensitiveEndpointRule(
        method="POST",
        pattern=re.compile(rf"/api/v1/districts/{_UUID_SEGMENT}/registrations"),
        limit_attribute="public_registration_limit",
    ),
)


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
        sensitive_fallback_config: SensitiveFallbackConfig | None = None,
    ) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.config = config or RateLimitConfig()
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}
        self.local_fallback_limiter = local_fallback_limiter or LocalFallbackRateLimiter()
        self.sensitive_fallback_config = sensitive_fallback_config or SensitiveFallbackConfig()

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
        fallback_config = self._sensitive_fallback_config(request.method, request.url.path)
        if (result.fail_open or burst_result.fail_open) and fallback_config is not None:
            rule_name, fallback_limit, fallback_window = fallback_config
            # Bucket per rule, not per raw path: otherwise every random district
            # UUID would open a new bucket and LRU eviction could reset the limit.
            local_result = await self.local_fallback_limiter.check(
                identifier=identifier,
                endpoint=rule_name,
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

    def _sensitive_fallback_config(self, method: str, path: str) -> tuple[str, int, int] | None:
        """Return (bucket name, limit, window) for a declared sensitive route."""
        for rule in SENSITIVE_ENDPOINT_RULES:
            if rule.matches(method, path):
                return (
                    rule.limit_attribute,
                    int(getattr(self.sensitive_fallback_config, rule.limit_attribute)),
                    self.sensitive_fallback_config.window_seconds,
                )
        return None

    def _get_identifier(self, request: Request) -> str:
        """Use a verified principal when available, otherwise the client IP."""
        user = getattr(request.state, "user", None)
        sub = getattr(user, "sub", None) if user else None
        if isinstance(sub, str) and sub:
            return f"user:{sub}"

        ip_address = get_client_ip(request)
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
