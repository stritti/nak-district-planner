"""Regression tests for security boundaries enforced before route dependencies."""

from datetime import timedelta
from unittest.mock import AsyncMock

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.adapters.api.middleware.rate_limit import RateLimitMiddleware
from app.adapters.api.middleware.tenant import TenantMiddleware
from app.application.local_rate_limiter import LocalFallbackRateLimiter
from app.application.rate_limiter import RateLimitResult


def request(path: str, *, authorization: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if authorization:
        headers.append((b"authorization", authorization.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "query_string": b"",
            "headers": headers,
            "client": ("203.0.113.10", 12345),
            "scheme": "https",
            "server": ("testserver", 443),
        }
    )


def fail_open_result(limit: int = 100) -> RateLimitResult:
    return RateLimitResult(
        allowed=True,
        remaining=limit,
        limit=limit,
        reset_in=timedelta(seconds=60),
        fail_open=True,
        fail_open_reason="ConnectionError",
    )


def fake_failed_primary_limiter() -> AsyncMock:
    limiter = AsyncMock()
    limiter.check_rate_limit.return_value = fail_open_result()
    limiter.check_burst_limit.return_value = fail_open_result(limit=10)
    limiter.get_rate_limit_headers.side_effect = lambda result: {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(int(result.reset_in.total_seconds())),
        **({"Retry-After": str(result.retry_after)} if result.retry_after else {}),
    }
    return limiter


def test_tenant_context_does_not_extract_unverified_bearer_subject() -> None:
    district_id = "11111111-1111-1111-1111-111111111111"
    # The payload encodes {"sub":"victim"}; its contents must be irrelevant to middleware.
    forged = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ2aWN0aW0ifQ."
    middleware = TenantMiddleware(FastAPI())

    context = middleware._extract_tenant_context(
        request(f"/api/v1/districts/{district_id}/leaders", authorization=f"Bearer {forged}")
    )

    assert "user_sub" not in context
    assert str(context["district_id"]) == district_id


def test_bearer_header_alone_is_not_authenticated_for_rate_multiplier() -> None:
    req = request("/api/v1/events", authorization="Bearer forged-token")

    assert RateLimitMiddleware._is_authenticated(req) is False


def test_sensitive_path_detection_is_narrow() -> None:
    district = "11111111-1111-1111-1111-111111111111"

    assert RateLimitMiddleware._is_sensitive_path("POST", "/api/v1/auth/oidc/token")
    assert RateLimitMiddleware._is_sensitive_path(
        "POST", f"/api/v1/districts/{district}/registrations"
    )
    assert not RateLimitMiddleware._is_sensitive_path(
        "POST", f"/api/v1/districts/{district}/registrations/abc/approve"
    )
    assert not RateLimitMiddleware._is_sensitive_path("GET", "/api/v1/auth/oidc/token")


def test_auth_token_endpoint_uses_local_limit_when_primary_fails_open() -> None:
    app = FastAPI()
    primary = fake_failed_primary_limiter()
    local = LocalFallbackRateLimiter()

    @app.post("/api/v1/auth/oidc/token")
    async def token_endpoint() -> Response:
        return Response("ok")

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=primary,
        local_fallback_limiter=local,
    )

    with TestClient(app) as client:
        for _ in range(30):
            assert client.post("/api/v1/auth/oidc/token").status_code == 200
        blocked = client.post("/api/v1/auth/oidc/token")

    assert blocked.status_code == 429
    assert blocked.headers["X-RateLimit-Limit"] == "30"


def test_public_registration_uses_stricter_local_limit_on_primary_failure() -> None:
    app = FastAPI()
    primary = fake_failed_primary_limiter()
    district = "11111111-1111-1111-1111-111111111111"
    path = f"/api/v1/districts/{district}/registrations"

    @app.post(path)
    async def registration_endpoint() -> Response:
        return Response("ok")

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=primary,
        local_fallback_limiter=LocalFallbackRateLimiter(),
    )

    with TestClient(app) as client:
        for _ in range(10):
            assert client.post(path).status_code == 200
        blocked = client.post(path)

    assert blocked.status_code == 429
    assert blocked.headers["X-RateLimit-Limit"] == "10"


def test_normal_business_endpoint_keeps_documented_fail_open_behavior() -> None:
    app = FastAPI()
    primary = fake_failed_primary_limiter()

    @app.post("/api/v1/events")
    async def events_endpoint() -> Response:
        return Response("ok")

    app.add_middleware(RateLimitMiddleware, rate_limiter=primary)

    with TestClient(app) as client:
        for _ in range(40):
            assert client.post("/api/v1/events").status_code == 200
