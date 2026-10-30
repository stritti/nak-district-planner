# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""OIDC gateway and access context failure cases without bypassing response handling."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from app.adapters.api.routers import auth as router
from app.adapters.auth.oidc import OIDCDiscoveryError
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


def _adapter() -> SimpleNamespace:
    return SimpleNamespace(
        client_id="planner",
        client_secret="client-secret",
        discover=AsyncMock(
            return_value={
                "token_endpoint": "https://idp.example/token",
                "revocation_endpoint": "https://idp.example/revoke",
            }
        ),
        get_httpx_client=AsyncMock(),
    )


def _token_request() -> router.OIDCTokenExchangeRequest:
    return router.OIDCTokenExchangeRequest(
        grant_type="authorization_code",
        code="one-time-code",
        redirect_uri="https://planner.example/callback",
        code_verifier="pkce-verifier",
    )


def _asgi_request(*, cookie: str | None = None):
    from starlette.requests import Request

    headers = [(b"cookie", cookie.encode())] if cookie else []
    return Request({
        "type": "http", "path": "/api/v1/auth/oidc/token",
        "method": "POST", "headers": headers,
    })


def _provider_response(*, code: int, payload: object = None, text: str = ""):
    response = MagicMock(spec=httpx.Response)
    response.is_success = 200 <= code < 300
    response.status_code = code
    response.json.return_value = payload
    response.text = text
    return response


@pytest.mark.asyncio
async def test_discovery_unavailable_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: None)
    with pytest.raises(HTTPException) as error:
        await router.get_oidc_discovery()
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_discovery_masks_revocation_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    out = await router.get_oidc_discovery()
    assert out["client_id"] == "planner"
    assert out["revocation_endpoint"] == "/api/v1/auth/oidc/revoke"
    assert out["token_endpoint"] == "https://idp.example/token"


@pytest.mark.asyncio
async def test_discovery_error_returns_bad_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _adapter()
    adapter.discover.side_effect = OIDCDiscoveryError("issuer unavailable")
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    with pytest.raises(HTTPException) as error:
        await router.get_oidc_discovery()
    assert error.value.status_code == 502


@pytest.mark.asyncio
async def test_discovery_failure_logs_neither_provider_url_nor_message(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    adapter = _adapter()
    adapter.discover.side_effect = OIDCDiscoveryError(
        "GET https://keycloak.internal.example:8443/realms/secret-realm failed"
    )
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    with caplog.at_level("DEBUG"), pytest.raises(HTTPException) as error:
        await router.get_oidc_discovery()
    assert "keycloak.internal" not in str(error.value.detail)
    assert "keycloak.internal" not in caplog.text
    assert "secret-realm" not in caplog.text
    assert "OIDC discovery failed" in caplog.text


@pytest.mark.asyncio
async def test_exchange_without_adapter_or_token_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: None)
    with pytest.raises(HTTPException) as missing:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), Response())
    assert missing.value.status_code == 503

    adapter = _adapter()
    adapter.discover.return_value = {}
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    with pytest.raises(HTTPException) as incomplete:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), Response())
    assert incomplete.value.status_code == 502
    adapter.get_httpx_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_exchange_propagates_safe_provider_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    client = SimpleNamespace(post=AsyncMock(side_effect=httpx.ConnectError("connection lost")))
    adapter.get_httpx_client.return_value = client
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)

    with pytest.raises(HTTPException) as error:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), Response())

    assert error.value.status_code == 502
    assert "Token exchange failed" in error.value.detail
    assert "connection lost" not in error.value.detail


@pytest.mark.asyncio
async def test_provider_error_body_is_reduced_to_oauth_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    response = _provider_response(
        code=400,
        payload={
            "error": "invalid_grant",
            "error_description": "internal realm 'secret-realm' stack trace",
            "debug": {"host": "keycloak.internal"},
        },
        text="internal body",
    )
    adapter.get_httpx_client.return_value = SimpleNamespace(
        post=AsyncMock(return_value=response)
    )
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    with pytest.raises(HTTPException) as error:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), Response())
    assert error.value.detail == {"error": "invalid_grant"}


@pytest.mark.asyncio
async def test_non_json_provider_error_body_is_not_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    response = _provider_response(code=500, payload=None, text="<html>internal trace</html>")
    response.json.side_effect = ValueError("not json")
    adapter.get_httpx_client.return_value = SimpleNamespace(
        post=AsyncMock(return_value=response)
    )
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    with pytest.raises(HTTPException) as error:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), Response())
    assert error.value.detail == {"error": "token_exchange_failed"}


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_json", [False, True])
async def test_failed_provider_response_preserves_status_without_cookie(
    monkeypatch: pytest.MonkeyPatch, invalid_json: bool
) -> None:
    adapter = _adapter()
    response = _provider_response(code=400, payload={"error": "invalid_grant"}, text="")
    if invalid_json:
        response.json.side_effect = ValueError("not json")
    adapter.get_httpx_client.return_value = SimpleNamespace(
        post=AsyncMock(return_value=response)
    )
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    output = Response()
    with pytest.raises(HTTPException) as error:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), output)
    assert error.value.status_code == 400
    if not invalid_json:
        assert error.value.detail == {"error": "invalid_grant"}
    assert router.REFRESH_COOKIE_NAME not in output.headers.get("set-cookie", "")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [["invalid"], {"refresh_token": 123}, {"refresh_token": ""}])
async def test_invalid_success_payload_returns_bad_gateway_without_cookie(
    monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    adapter = _adapter()
    adapter.get_httpx_client.return_value = SimpleNamespace(
        post=AsyncMock(return_value=_provider_response(code=200, payload=payload))
    )
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    output = Response()
    with pytest.raises(HTTPException) as error:
        await router.exchange_oidc_token(_token_request(), _asgi_request(), output)
    assert error.value.status_code == 502
    assert router.REFRESH_COOKIE_NAME not in output.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_revoke_with_no_revocation_endpoint_still_clears_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    adapter.discover.return_value = {}
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    response = await router.revoke_oidc_refresh_token(
        _asgi_request(cookie=f"{router.REFRESH_COOKIE_NAME}=secret")
    )
    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    adapter.get_httpx_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_discovery_error_still_clears_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _adapter()
    adapter.discover.side_effect = OIDCDiscoveryError("idp unavailable")
    monkeypatch.setattr(router, "get_oidc_adapter", lambda: adapter)
    response = await router.revoke_oidc_refresh_token(
        _asgi_request(cookie=f"{router.REFRESH_COOKIE_NAME}=secret")
    )
    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_congregation_only_member_has_active_access() -> None:
    congregations = [uuid.uuid4(), uuid.uuid4()]
    auth = SimpleNamespace(
        user=SimpleNamespace(is_superadmin=False),
        memberships=[
            Membership.create(
                user_sub="operator",
                role=role,
                scope_type=ScopeType.CONGREGATION,
                scope_id=congregation,
            )
            for role, congregation in zip(
                (Role.CONGREGATION_ADMIN, Role.VIEWER), congregations, strict=True
            )
        ],
    )
    result = await router.get_access_context(auth)
    assert result.status == "ACTIVE"
    assert [(m.role, m.scope_type, m.scope_id) for m in result.memberships] == [
        ("CONGREGATION_ADMIN", "CONGREGATION", str(congregations[0])),
        ("VIEWER", "CONGREGATION", str(congregations[1])),
    ]


@pytest.mark.asyncio
async def test_revoked_superadmin_without_memberships_is_pending_again() -> None:
    auth = SimpleNamespace(user=SimpleNamespace(is_superadmin=False), memberships=[])
    result = await router.get_access_context(auth)
    assert result.status == "PENDING_APPROVAL"
    assert result.is_superadmin is False


@pytest.mark.asyncio
async def test_superadmin_without_memberships_has_active_access() -> None:
    auth = SimpleNamespace(
        user=SimpleNamespace(is_superadmin=True),
        memberships=[],
    )
    result = await router.get_access_context(auth)
    assert result.status == "ACTIVE"
    assert result.memberships == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"grant_type": "authorization_code", "code": None, "code_verifier": "x", "redirect_uri": "x"},
        {"grant_type": "authorization_code", "code": "x", "code_verifier": None, "redirect_uri": "x"},
        {"grant_type": "authorization_code", "code": "x", "code_verifier": "x", "redirect_uri": None},
        {"grant_type": "not-a-grant"},
    ],
)
def test_invalid_grant_parameters_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        router.OIDCTokenExchangeRequest(**kwargs)
