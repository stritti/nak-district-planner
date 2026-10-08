"""Regression tests for security boundaries enforced before route dependencies."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.adapters.api.middleware.rate_limit import (
    RateLimitMiddleware,
    SensitiveFallbackConfig,
)
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


def test_sensitive_route_registry_is_narrow_and_configurable() -> None:
    district = "11111111-1111-1111-1111-111111111111"
    middleware = RateLimitMiddleware(
        FastAPI(),
        sensitive_fallback_config=SensitiveFallbackConfig(
            auth_token_limit=7,
            public_registration_limit=3,
            window_seconds=45,
        ),
    )

    assert middleware._sensitive_fallback_config("POST", "/api/v1/auth/oidc/token") == (
        "auth_token_limit",
        7,
        45,
    )
    assert middleware._sensitive_fallback_config(
        "POST", f"/api/v1/districts/{district}/registrations"
    ) == ("public_registration_limit", 3, 45)
    assert (
        middleware._sensitive_fallback_config(
            "POST", f"/api/v1/districts/{district}/registrations/abc/approve"
        )
        is None
    )
    assert middleware._sensitive_fallback_config("GET", "/api/v1/auth/oidc/token") is None
    assert middleware._sensitive_fallback_config(
        "POST", "/api/v1/districts/not-a-uuid/registrations"
    ) is None


def test_auth_token_endpoint_uses_local_limit_when_primary_fails_open() -> None:
    app = FastAPI()
    primary = fake_failed_primary_limiter()

    @app.post("/api/v1/auth/oidc/token")
    async def token_endpoint() -> Response:
        return Response("ok")

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=primary,
        local_fallback_limiter=LocalFallbackRateLimiter(),
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


@pytest.mark.asyncio
async def test_local_fallback_cleanup_is_amortized() -> None:
    limiter = LocalFallbackRateLimiter(max_buckets=8, cleanup_every=2)

    with patch("app.application.local_rate_limiter.time.monotonic", side_effect=[0.0, 2.0]):
        await limiter.check(
            identifier="ip:a",
            endpoint="/sensitive",
            limit=10,
            window_seconds=1,
        )
        await limiter.check(
            identifier="ip:b",
            endpoint="/sensitive",
            limit=10,
            window_seconds=1,
        )

    assert list(limiter._buckets) == ["ip:b:/sensitive"]


@pytest.mark.asyncio
async def test_local_fallback_bucket_cap_is_enforced_without_global_scan() -> None:
    limiter = LocalFallbackRateLimiter(max_buckets=2, cleanup_every=100)

    for identifier in ("ip:a", "ip:b", "ip:c"):
        await limiter.check(
            identifier=identifier,
            endpoint="/sensitive",
            limit=10,
            window_seconds=60,
        )

    assert len(limiter._buckets) == 2
    assert "ip:a:/sensitive" not in limiter._buckets


def registration_app(limiter: LocalFallbackRateLimiter, primary: AsyncMock | None = None) -> FastAPI:
    app = FastAPI()

    @app.post("/api/v1/districts/{district_id}/registrations")
    async def registration_endpoint(district_id: str) -> Response:
        return Response("ok")

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=primary or fake_failed_primary_limiter(),
        local_fallback_limiter=limiter,
    )
    return app


def test_registration_fallback_cannot_be_reset_by_evicting_own_bucket() -> None:
    """Random district UUIDs must share one bucket, so LRU eviction is no bypass."""
    import uuid

    app = registration_app(LocalFallbackRateLimiter(max_buckets=8))
    target = "/api/v1/districts/11111111-1111-1111-1111-111111111111/registrations"

    with TestClient(app) as client:
        for _ in range(10):
            assert client.post(target).status_code == 200
        for _ in range(20):
            client.post(f"/api/v1/districts/{uuid.uuid4()}/registrations")
        blocked = client.post(target)

    assert blocked.status_code == 429


def test_local_fallback_applies_when_only_burst_check_fails_open() -> None:
    primary = fake_failed_primary_limiter()
    primary.check_rate_limit.return_value = RateLimitResult(
        allowed=True, remaining=99, limit=100, reset_in=timedelta(seconds=60)
    )
    app = registration_app(LocalFallbackRateLimiter(), primary)
    path = "/api/v1/districts/11111111-1111-1111-1111-111111111111/registrations"

    with TestClient(app) as client:
        for _ in range(10):
            assert client.post(path).status_code == 200
        assert client.post(path).status_code == 429


def test_local_fallback_buckets_are_separated_by_identifier() -> None:
    app = registration_app(LocalFallbackRateLimiter())
    path = "/api/v1/districts/11111111-1111-1111-1111-111111111111/registrations"

    # Requests arrive via the trusted frontend nginx, which sets X-Real-IP.
    with TestClient(app, client=("172.18.0.5", 40000)) as client:
        for _ in range(10):
            client.post(path, headers={"X-Real-IP": "198.51.100.1"})
        assert client.post(path, headers={"X-Real-IP": "198.51.100.1"}).status_code == 429
        assert client.post(path, headers={"X-Real-IP": "198.51.100.2"}).status_code == 200


@pytest.mark.asyncio
async def test_single_key_flood_keeps_bucket_bounded_by_limit() -> None:
    limiter = LocalFallbackRateLimiter()

    results = [
        await limiter.check(identifier="ip:a", endpoint="rule", limit=3, window_seconds=60)
        for _ in range(1000)
    ]

    assert [r.allowed for r in results[:4]] == [True, True, True, False]
    assert not any(r.allowed for r in results[3:])
    assert len(limiter._buckets["ip:a:rule"]) == 3
