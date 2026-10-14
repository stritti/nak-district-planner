# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Client IP resolution behind the trusted nginx proxy (issue #462)."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.adapters.api.client_ip import get_client_ip
from app.adapters.api.middleware.audit import AuditMiddleware
from app.adapters.api.middleware.rate_limit import RateLimitMiddleware
from app.application.local_rate_limiter import LocalFallbackRateLimiter
from app.config import Settings
from tests.unit.test_security_boundary_middleware import fake_failed_primary_limiter

NGINX_PEER = ("172.18.0.5", 40000)
UNTRUSTED_PEER = ("203.0.113.9", 40000)


def make_request(peer: tuple[str, int] | None, headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": peer,
    }
    return Request(scope)


def test_trusted_proxy_x_real_ip_is_used() -> None:
    request = make_request(NGINX_PEER, {"X-Real-IP": "198.51.100.7"})
    assert get_client_ip(request) == "198.51.100.7"


def test_untrusted_peer_cannot_spoof_forwarding_headers() -> None:
    request = make_request(
        UNTRUSTED_PEER,
        {"X-Real-IP": "198.51.100.7", "X-Forwarded-For": "198.51.100.8"},
    )
    assert get_client_ip(request) == "203.0.113.9"


def test_x_forwarded_for_is_never_trusted() -> None:
    request = make_request(NGINX_PEER, {"X-Forwarded-For": "198.51.100.8, 10.0.0.1"})
    assert get_client_ip(request) == "172.18.0.5"


def test_invalid_x_real_ip_falls_back_to_peer() -> None:
    request = make_request(NGINX_PEER, {"X-Real-IP": "not-an-ip"})
    assert get_client_ip(request) == "172.18.0.5"


def test_missing_peer_returns_none() -> None:
    assert get_client_ip(make_request(None, {"X-Real-IP": "198.51.100.7"})) is None


def test_trusted_proxies_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.adapters.api import client_ip

    monkeypatch.setattr(client_ip.settings, "trusted_proxies", "10.1.2.3/32")
    request = make_request(NGINX_PEER, {"X-Real-IP": "198.51.100.7"})
    assert get_client_ip(request) == "172.18.0.5"
    request = make_request(("10.1.2.3", 1), {"X-Real-IP": "198.51.100.7"})
    assert get_client_ip(request) == "198.51.100.7"


def test_invalid_trusted_proxies_setting_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(trusted_proxies="127.0.0.1/32,not-a-network")


def test_clients_behind_proxy_get_separate_rate_limit_buckets() -> None:
    primary = fake_failed_primary_limiter()
    app = FastAPI()

    @app.post("/api/v1/auth/oidc/token")
    async def token() -> Response:
        return Response("ok")

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=primary,
        local_fallback_limiter=LocalFallbackRateLimiter(),
    )
    path = "/api/v1/auth/oidc/token"

    with TestClient(app, client=NGINX_PEER) as client:
        for _ in range(30):
            client.post(path, headers={"X-Real-IP": "198.51.100.1"})
        assert client.post(path, headers={"X-Real-IP": "198.51.100.1"}).status_code == 429
        assert client.post(path, headers={"X-Real-IP": "198.51.100.2"}).status_code == 200

    with TestClient(app, client=UNTRUSTED_PEER) as client:
        for _ in range(30):
            client.post(path, headers={"X-Real-IP": "198.51.100.3"})
        # Rotating spoofed headers from an untrusted peer does not escape the bucket.
        assert client.post(path, headers={"X-Real-IP": "198.51.100.4"}).status_code == 429


def test_audit_middleware_uses_shared_client_ip() -> None:
    middleware = AuditMiddleware(app=MagicMock())
    request = make_request(UNTRUSTED_PEER, {"X-Forwarded-For": "1.2.3.4"})
    assert middleware._get_client_ip(request) == "203.0.113.9"
    request = make_request(NGINX_PEER, {"X-Real-IP": "198.51.100.7"})
    assert middleware._get_client_ip(request) == "198.51.100.7"
