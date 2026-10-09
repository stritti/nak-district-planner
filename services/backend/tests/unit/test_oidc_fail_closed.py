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
async def test_opaque_token_requires_introspection_even_with_valid_userinfo(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        return_value={"sub": "opaque-user", "iss": "https://oidc.example.com"}
    )
    adapter._introspect_token = AsyncMock(
        side_effect=TokenValidationError("introspection unavailable")
    )

    with pytest.raises(TokenValidationError, match="introspection unavailable"):
        await adapter.validate_token("opaque-token")

    adapter._fetch_userinfo_claims.assert_not_awaited()


@pytest.mark.asyncio
async def test_opaque_token_with_client_bound_introspection_can_use_userinfo(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        return_value={"sub": "opaque-user", "iss": "https://oidc.example.com"}
    )
    adapter._introspect_token = AsyncMock(
        return_value={"active": True, "sub": "opaque-user", "client_id": "planner-client"}
    )

    claims = await adapter.validate_token("opaque-token")

    assert claims["sub"] == "opaque-user"
    adapter._introspect_token.assert_awaited_once_with("opaque-token")
    adapter._fetch_userinfo_claims.assert_awaited_once_with("opaque-token")


@pytest.mark.asyncio
async def test_opaque_userinfo_claim_mismatch_is_terminal(
    adapter: OIDCAdapter,
) -> None:
    adapter._fetch_userinfo_claims = AsyncMock(
        return_value={"sub": "opaque-user", "iss": "https://evil.example.com"}
    )
    adapter._introspect_token = AsyncMock(
        return_value={"active": True, "sub": "opaque-user", "client_id": "planner-client"}
    )

    with pytest.raises(TokenValidationError, match="Invalid issuer"):
        await adapter.validate_token("opaque-token")

    adapter._introspect_token.assert_awaited_once_with("opaque-token")


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
async def test_opaque_audience_cannot_be_replaced_by_matching_azp(
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
            "azp": "planner-client",
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


@pytest.mark.asyncio
async def test_opaque_introspection_rejects_missing_client_id(adapter: OIDCAdapter) -> None:
    adapter._introspect_token = AsyncMock(
        return_value={"active": True, "sub": "opaque-user", "aud": "planner-client"}
    )
    adapter._fetch_userinfo_claims = AsyncMock()

    with pytest.raises(TokenValidationError, match="not issued to this client"):
        await adapter.validate_token("opaque-token")

    adapter._fetch_userinfo_claims.assert_not_awaited()


@pytest.mark.asyncio
async def test_opaque_introspection_rejects_wrong_client_before_userinfo(
    adapter: OIDCAdapter,
) -> None:
    adapter._introspect_token = AsyncMock(
        return_value={"active": True, "sub": "opaque-user", "client_id": "other-client"}
    )
    adapter._fetch_userinfo_claims = AsyncMock(
        return_value={"sub": "opaque-user", "email_verified": True}
    )

    with pytest.raises(TokenValidationError, match="not issued to this client"):
        await adapter.validate_token("opaque-token")

    adapter._fetch_userinfo_claims.assert_not_awaited()


@pytest.mark.asyncio
async def test_opaque_userinfo_subject_must_equal_introspection_subject(
    adapter: OIDCAdapter,
) -> None:
    adapter._introspect_token = AsyncMock(
        return_value={"active": True, "sub": "alice", "client_id": "planner-client"}
    )
    adapter._fetch_userinfo_claims = AsyncMock(return_value={"sub": "bob"})

    with pytest.raises(TokenValidationError, match="subject mismatch"):
        await adapter.validate_token("opaque-token")


@pytest.mark.asyncio
async def test_opaque_userinfo_outage_preserves_validated_introspection(
    adapter: OIDCAdapter,
) -> None:
    adapter._introspect_token = AsyncMock(
        return_value={"active": True, "sub": "alice", "client_id": "planner-client"}
    )
    adapter._fetch_userinfo_claims = AsyncMock(
        side_effect=TokenValidationError("userinfo unavailable")
    )

    assert (await adapter.validate_token("opaque-token"))["sub"] == "alice"


@pytest.mark.asyncio
async def test_opaque_introspection_rejects_non_boolean_active(adapter: OIDCAdapter) -> None:
    from datetime import UTC, datetime

    adapter._discovery_cache = {"introspection_endpoint": "https://oidc.example.com/introspect"}
    adapter._discovery_cache_time = datetime.now(UTC)
    from unittest.mock import MagicMock
    import httpx

    httpx_client = AsyncMock(spec=httpx.AsyncClient)
    provider_response = MagicMock(spec=httpx.Response)
    provider_response.status_code = 200
    provider_response.json.return_value = {
        "active": "false", "sub": "opaque-user", "client_id": "planner-client"
    }
    httpx_client.post.return_value = provider_response
    adapter._httpx_client = httpx_client

    with pytest.raises(TokenValidationError, match="inactive"):
        await adapter.validate_token("opaque-token")
