from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.adapters.api.routers import auth as r
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


def request_with_cookie(cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/oidc/token",
            "headers": headers,
        }
    )


def adapter_for_response(payload: dict) -> SimpleNamespace:
    provider_response = SimpleNamespace(
        is_success=True,
        json=lambda: payload,
    )
    client = SimpleNamespace(post=AsyncMock(return_value=provider_response))
    return SimpleNamespace(
        client_id="client-id",
        client_secret="client-secret",
        discover=AsyncMock(
            return_value={
                "token_endpoint": "https://issuer.example/token",
                "revocation_endpoint": "https://issuer.example/revoke",
            }
        ),
        get_httpx_client=AsyncMock(return_value=client),
        _client=client,
    )


@pytest.mark.asyncio
async def test_exchange_oidc_token_uses_http_only_cookie_for_refresh_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = adapter_for_response(
        {
            "access_token": "new-access",
            "refresh_token": "rotated-provider-refresh",
            "expires_in": 3600,
        }
    )
    monkeypatch.setattr(r, "get_oidc_adapter", lambda: adapter)

    response = Response()
    payload = await r.exchange_oidc_token(
        r.OIDCTokenExchangeRequest(
            grant_type="refresh_token",
            refresh_token=r.REFRESH_COORDINATION_MARKER,
        ),
        request_with_cookie(f"{r.REFRESH_COOKIE_NAME}=provider-refresh"),
        response,
    )

    adapter._client.post.assert_awaited_once_with(
        "https://issuer.example/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": "provider-refresh",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
        timeout=15,
    )
    assert payload["access_token"] == "new-access"
    assert payload["refresh_token"] == r.REFRESH_COORDINATION_MARKER
    assert "rotated-provider-refresh" not in str(payload)
    cookie_header = response.headers["set-cookie"]
    assert r.REFRESH_COOKIE_NAME in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=strict" in cookie_header


@pytest.mark.asyncio
async def test_authorization_code_exchange_hides_provider_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = adapter_for_response(
        {
            "access_token": "access",
            "id_token": "id-token",
            "refresh_token": "provider-secret",
            "expires_in": 3600,
        }
    )
    monkeypatch.setattr(r, "get_oidc_adapter", lambda: adapter)

    response = Response()
    payload = await r.exchange_oidc_token(
        r.OIDCTokenExchangeRequest(
            grant_type="authorization_code",
            code="code",
            redirect_uri="https://planner.example/auth/callback",
            code_verifier="verifier",
        ),
        request_with_cookie(),
        response,
    )

    assert payload["refresh_token"] == r.REFRESH_COORDINATION_MARKER
    assert "provider-secret" not in str(payload)
    assert "provider-secret" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_refresh_grant_without_cookie_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = adapter_for_response({"access_token": "unused"})
    monkeypatch.setattr(r, "get_oidc_adapter", lambda: adapter)

    with pytest.raises(HTTPException) as exc_info:
        await r.exchange_oidc_token(
            r.OIDCTokenExchangeRequest(
                grant_type="refresh_token",
                refresh_token=r.REFRESH_COORDINATION_MARKER,
            ),
            request_with_cookie(),
            Response(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {"error": "missing_refresh_cookie"}
    adapter._client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_rotating_provider_keeps_frontend_coordination_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = adapter_for_response({"access_token": "new-access", "expires_in": 3600})
    monkeypatch.setattr(r, "get_oidc_adapter", lambda: adapter)

    payload = await r.exchange_oidc_token(
        r.OIDCTokenExchangeRequest(
            grant_type="refresh_token",
            refresh_token=r.REFRESH_COORDINATION_MARKER,
        ),
        request_with_cookie(f"{r.REFRESH_COOKIE_NAME}=provider-refresh"),
        Response(),
    )

    assert payload["refresh_token"] == r.REFRESH_COORDINATION_MARKER


@pytest.mark.asyncio
async def test_revoke_uses_server_held_refresh_token_and_deletes_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = adapter_for_response({"access_token": "unused"})
    monkeypatch.setattr(r, "get_oidc_adapter", lambda: adapter)

    response = Response()
    result = await r.revoke_oidc_refresh_token(
        request_with_cookie(f"{r.REFRESH_COOKIE_NAME}=provider-refresh"),
        response,
    )

    adapter._client.post.assert_awaited_once_with(
        "https://issuer.example/revoke",
        data={
            "token": "provider-refresh",
            "token_type_hint": "refresh_token",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
        timeout=10,
    )
    assert result.status_code == 204
    cookie_header = result.headers["set-cookie"]
    assert r.REFRESH_COOKIE_NAME in cookie_header
    assert "Max-Age=0" in cookie_header


@pytest.mark.asyncio
async def test_get_current_user_info_maps_authenticated_user_fields() -> None:
    user = SimpleNamespace(
        sub="user-sub",
        email="test@example.org",
        username="tester",
        name="Test User",
        given_name="Test",
        family_name="User",
        is_superadmin=True,
    )

    out = await r.get_current_user_info(user)

    assert out.sub == "user-sub"
    assert out.email == "test@example.org"
    assert out.is_superadmin is True


@pytest.mark.asyncio
async def test_get_access_context_for_memberships_and_pending_approval() -> None:
    district_id = uuid.uuid4()
    auth_with_memberships = SimpleNamespace(
        user=SimpleNamespace(is_superadmin=False),
        memberships=[
            Membership.create(
                user_sub="user-sub",
                role=Role.PLANNER,
                scope_type=ScopeType.DISTRICT,
                scope_id=district_id,
            )
        ],
    )

    out_active = await r.get_access_context(auth_with_memberships)
    assert out_active.status == "ACTIVE"
    assert out_active.memberships[0].scope_id == str(district_id)

    auth_pending = SimpleNamespace(user=SimpleNamespace(is_superadmin=False), memberships=[])
    out_pending = await r.get_access_context(auth_pending)
    assert out_pending.status == "PENDING_APPROVAL"
    assert out_pending.memberships == []
