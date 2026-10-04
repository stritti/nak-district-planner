"""Regression tests for fail-closed OIDC token validation."""

from unittest.mock import AsyncMock

import pytest

from app.adapters.auth.oidc import OIDCAdapter, TokenValidationError


@pytest.fixture
def adapter() -> OIDCAdapter:
    return OIDCAdapter(
        discovery_url="https://oidc.example.com/.well-known/openid-configuration",
        client_id="planner-client",
        client_secret="secret",
        issuer="https://oidc.example.com",
    )


@pytest.mark.asyncio
async def test_jwt_validation_failure_never_falls_back_to_opaque_paths(
    adapter: OIDCAdapter,
) -> None:
    adapter._validate_jwt_token = AsyncMock(
        side_effect=TokenValidationError("invalid audience")
    )
    adapter._fetch_userinfo_claims = AsyncMock()
    adapter._introspect_token = AsyncMock()

    with pytest.raises(TokenValidationError, match="invalid audience"):
        await adapter.validate_token("header.payload.signature")

    adapter._fetch_userinfo_claims.assert_not_awaited()
    adapter._introspect_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_jwt_validation_defaults_to_rs256_only(adapter: OIDCAdapter) -> None:
    adapter._validate_jwt_token = AsyncMock(return_value={"sub": "user-1"})

    claims = await adapter.validate_token("header.payload.signature")

    assert claims["sub"] == "user-1"
    adapter._validate_jwt_token.assert_awaited_once_with(
        token="header.payload.signature",
        audience="planner-client",
        algorithms=["RS256"],
    )


@pytest.mark.asyncio
async def test_opaque_token_can_use_userinfo(adapter: OIDCAdapter) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        return_value={"sub": "opaque-user", "iss": "https://oidc.example.com"}
    )
    adapter._introspect_token = AsyncMock()

    claims = await adapter.validate_token("opaque-token")

    assert claims["sub"] == "opaque-user"
    adapter._introspect_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_opaque_userinfo_with_wrong_issuer_falls_through_and_fails(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        return_value={"sub": "opaque-user", "iss": "https://evil.example.com"}
    )
    adapter._introspect_token = AsyncMock(
        side_effect=TokenValidationError("introspection unavailable")
    )

    with pytest.raises(TokenValidationError, match="Opaque token validation failed"):
        await adapter.validate_token("opaque-token")

    adapter._introspect_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_opaque_introspection_rejects_wrong_client_id(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        side_effect=TokenValidationError("userinfo unavailable")
    )
    adapter._introspect_token = AsyncMock(
        return_value={
            "active": True,
            "sub": "opaque-user",
            "client_id": "different-client",
        }
    )

    with pytest.raises(TokenValidationError, match="Invalid client_id"):
        await adapter.validate_token("opaque-token")


@pytest.mark.asyncio
async def test_opaque_introspection_rejects_wrong_audience(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        side_effect=TokenValidationError("userinfo unavailable")
    )
    adapter._introspect_token = AsyncMock(
        return_value={
            "active": True,
            "sub": "opaque-user",
            "aud": ["some-other-api"],
        }
    )

    with pytest.raises(TokenValidationError, match="Invalid audience"):
        await adapter.validate_token("opaque-token")


@pytest.mark.asyncio
async def test_unexpected_introspection_bug_is_not_hidden_as_invalid_token(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        side_effect=TokenValidationError("userinfo unavailable")
    )
    adapter._introspect_token = AsyncMock(side_effect=AttributeError("programming bug"))

    with pytest.raises(AttributeError, match="programming bug"):
        await adapter.validate_token("opaque-token")
