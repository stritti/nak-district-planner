"""Unit tests for OIDCAdapter — OIDC discovery, JWKS caching, JWT validation.

Tests use mocked OIDC provider responses to ensure provider-agnostic behavior.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.auth.oidc import (
    JWKSFetchError,
    OIDCAdapter,
    OIDCDiscoveryError,
    TokenValidationError,
)

# Mock OIDC discovery response
MOCK_DISCOVERY = {
    "issuer": "https://oidc.example.com",
    "authorization_endpoint": "https://oidc.example.com/oauth/authorize",
    "token_endpoint": "https://oidc.example.com/oauth/token",
    "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo",
    "jwks_uri": "https://oidc.example.com/oauth/certs",
}

# Mock JWKS response (with a test key)
MOCK_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "test-key-id",
            "use": "sig",
            "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
            "e": "AQAB",
        }
    ]
}


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def oidc_adapter(mock_httpx_client):
    """Create an OIDCAdapter with mocked httpx client."""
    return OIDCAdapter(
        discovery_url="https://oidc.example.com/.well-known/openid-configuration",
        client_id="test-client",
        client_secret="test-secret",
        httpx_client=mock_httpx_client,
    )


class TestOIDCDiscovery:
    """Test OIDC discovery functionality."""

    @pytest.mark.asyncio
    async def test_discover_success(self, oidc_adapter, mock_httpx_client):
        """Test successful OIDC discovery."""
        mock_httpx_client.get.return_value = AsyncMock(
            status_code=200,
            json=lambda: MOCK_DISCOVERY,
        )

        result = await oidc_adapter.discover()

        assert result == MOCK_DISCOVERY
        assert oidc_adapter.issuer == "https://oidc.example.com"
        mock_httpx_client.get.assert_called_once_with(
            "https://oidc.example.com/.well-known/openid-configuration",
            timeout=10,
        )

    @pytest.mark.asyncio
    async def test_discover_caching(self, oidc_adapter, mock_httpx_client):
        """Test that discovery result is cached."""
        mock_httpx_client.get.return_value = AsyncMock(
            status_code=200,
            json=lambda: MOCK_DISCOVERY,
        )

        # First call
        result1 = await oidc_adapter.discover()
        # Second call (should use cache)
        result2 = await oidc_adapter.discover()

        assert result1 == result2
        # httpx.get should only be called once due to caching
        assert mock_httpx_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_discover_http_error(self, oidc_adapter, mock_httpx_client):
        """Test discovery fails on HTTP error."""
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(OIDCDiscoveryError):
            await oidc_adapter.discover()

    @pytest.mark.asyncio
    async def test_discover_invalid_json(self, oidc_adapter, mock_httpx_client):
        """Test discovery fails on invalid JSON response."""
        mock_response = AsyncMock()
        mock_response.json = MagicMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        mock_httpx_client.get.return_value = mock_response

        with pytest.raises(OIDCDiscoveryError):
            await oidc_adapter.discover()


class TestJWKSFetching:
    """Test JWKS fetching and caching."""

    @pytest.mark.asyncio
    async def test_fetch_jwks_success(self, oidc_adapter, mock_httpx_client):
        """Test successful JWKS fetch."""
        # Mock discover call
        mock_discover_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_DISCOVERY,
        )
        # Mock JWKS call
        mock_jwks_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_JWKS,
        )

        mock_httpx_client.get.side_effect = [mock_discover_response, mock_jwks_response]

        result = await oidc_adapter.fetch_jwks()

        assert result == MOCK_JWKS
        assert len(result["keys"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_jwks_caching(self, oidc_adapter, mock_httpx_client):
        """Test that JWKS is cached."""
        mock_discover_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_DISCOVERY,
        )
        mock_jwks_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_JWKS,
        )

        mock_httpx_client.get.side_effect = [mock_discover_response, mock_jwks_response]

        # First call
        result1 = await oidc_adapter.fetch_jwks()
        # Second call (should use cache)
        result2 = await oidc_adapter.fetch_jwks()

        assert result1 == result2
        # Should only be 2 calls total (1 discover + 1 JWKS), not 3
        assert mock_httpx_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_jwks_fallback_to_stale_cache(self, oidc_adapter, mock_httpx_client):
        """Test JWKS fetch fallback to stale cache on error."""
        mock_discover_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_DISCOVERY,
        )
        mock_jwks_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_JWKS,
        )

        # First: successful fetch
        mock_httpx_client.get.side_effect = [mock_discover_response, mock_jwks_response]
        result1 = await oidc_adapter.fetch_jwks()
        assert result1 == MOCK_JWKS

        # Second: JWKS fetch fails, should fallback to stale cache
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection failed")
        result2 = await oidc_adapter.fetch_jwks(force_refresh=True)

        assert result2 == MOCK_JWKS  # Stale cache returned

    @pytest.mark.asyncio
    async def test_fetch_jwks_no_cache_on_error(self, oidc_adapter, mock_httpx_client):
        """Test JWKS fetch raises error when no cache and fetch fails."""
        # Mock discover success but JWKS fetch fails
        mock_discover_response = AsyncMock(
            status_code=200,
            json=lambda: MOCK_DISCOVERY,
        )
        mock_httpx_client.get.side_effect = [
            mock_discover_response,
            httpx.ConnectError("JWKS fetch failed"),
        ]

        with pytest.raises(JWKSFetchError):
            await oidc_adapter.fetch_jwks()


class TestUserInfoExtraction:
    """Test user info extraction from token claims."""

    def test_extract_user_info_full(self, oidc_adapter):
        """Test user info extraction with all fields."""
        claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "preferred_username": "john.doe",
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
        }

        result = oidc_adapter.extract_user_info(claims)

        assert result["sub"] == "user-123"
        assert result["email"] == "user@example.com"
        assert result["username"] == "john.doe"
        assert result["name"] == "John Doe"

    def test_extract_user_info_minimal(self, oidc_adapter):
        """Test user info extraction with minimal fields."""
        claims = {
            "sub": "user-456",
            "email": "user@example.com",
        }

        result = oidc_adapter.extract_user_info(claims)

        assert result["sub"] == "user-456"
        assert result["email"] == "user@example.com"
        assert result["username"] == "user@example.com"  # Falls back to email

    def test_extract_user_info_fallback_to_email(self, oidc_adapter):
        """Test username falls back to email when preferred_username is missing."""
        claims = {
            "sub": "user-789",
            "email": "jane@example.com",
        }

        result = oidc_adapter.extract_user_info(claims)

        assert result["username"] == "jane@example.com"


class TestTokenValidation:
    """Test JWT token validation (mocked, as real JWT signing is complex)."""

    @pytest.mark.asyncio
    async def test_validate_token_invalid_token(self, oidc_adapter, mock_httpx_client):
        """Test validation with invalid token."""
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo invalid")
        )
        with pytest.raises(TokenValidationError):
            await oidc_adapter.validate_token("invalid-token")

    @pytest.mark.asyncio
    async def test_extract_user_info_called_in_validate(self, oidc_adapter, mock_httpx_client):
        """Test that user info extraction is available after validation."""
        # This test is limited due to JWT signing complexity
        # In production, integration tests with real OIDC provider are recommended
        pass

    @pytest.mark.asyncio
    async def test_validate_token_falls_back_to_userinfo(self, oidc_adapter):
        """Opaque/non-JWT access tokens should be validated via userinfo endpoint."""
        oidc_adapter._validate_jwt_token = AsyncMock(side_effect=TokenValidationError("not a jwt"))
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            return_value={
                "sub": "user-opaque-123",
                "email": "opaque@example.com",
            }
        )

        claims = await oidc_adapter.validate_token("opaque-access-token")

        assert claims["sub"] == "user-opaque-123"
        oidc_adapter._fetch_userinfo_claims.assert_called_once_with("opaque-access-token")

    @pytest.mark.asyncio
    async def test_validate_token_raises_when_jwt_and_userinfo_fail(self, oidc_adapter):
        """Validation should fail if both JWT and userinfo checks fail."""
        oidc_adapter._validate_jwt_token = AsyncMock(
            side_effect=TokenValidationError("jwt invalid")
        )
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo invalid")
        )

        with pytest.raises(TokenValidationError):
            await oidc_adapter.validate_token("bad-token")

    def test_validate_audience_claims_accepts_azp(self, oidc_adapter):
        """Audience validation accepts azp when aud does not match directly."""
        claims = {"aud": ["some-api"], "azp": "test-client"}

        oidc_adapter._validate_audience_claims(claims, "test-client")

    def test_validate_audience_string_match(self, oidc_adapter):
        """Audience validation accepts string aud match."""
        claims = {"aud": "test-client"}
        oidc_adapter._validate_audience_claims(claims, "test-client")

    def test_validate_audience_no_match_raises(self, oidc_adapter):
        """Audience validation raises when neither aud nor azp match."""
        claims = {"aud": ["other-api"], "azp": "other-client"}
        with pytest.raises(TokenValidationError, match="audience"):
            oidc_adapter._validate_audience_claims(claims, "test-client")

    def test_validate_audience_list_match(self, oidc_adapter):
        """Audience validation accepts list aud containing expected."""
        claims = {"aud": ["api1", "test-client", "api2"]}
        oidc_adapter._validate_audience_claims(claims, "test-client")


class TestIntrospection:
    @pytest.mark.asyncio
    async def test_introspect_token_success(self, oidc_adapter, mock_httpx_client):
        """Successful introspection returns claims."""
        oidc_adapter._discovery_cache = {
            "introspection_endpoint": "https://oidc.example.com/oauth/introspect"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(return_value={"active": True, "sub": "user-123"})
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        claims = await oidc_adapter._introspect_token("some-token")

        assert claims["sub"] == "user-123"
        assert claims["active"] is True

    @pytest.mark.asyncio
    async def test_introspect_token_inactive(self, oidc_adapter, mock_httpx_client):
        """Inactive token raises error."""
        oidc_adapter._discovery_cache = {
            "introspection_endpoint": "https://oidc.example.com/oauth/introspect"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(return_value={"active": False})
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="inactive"):
            await oidc_adapter._introspect_token("bad-token")

    @pytest.mark.asyncio
    async def test_introspect_token_missing_endpoint(self, oidc_adapter, mock_httpx_client):
        """Missing introspection endpoint raises error."""
        oidc_adapter._discovery_cache = {}
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        with pytest.raises(TokenValidationError, match="introspection endpoint"):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_introspect_token_http_error(self, oidc_adapter, mock_httpx_client):
        """HTTP error during introspection raises error."""
        oidc_adapter._discovery_cache = {
            "introspection_endpoint": "https://oidc.example.com/oauth/introspect"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_httpx_client.post = AsyncMock(side_effect=httpx.HTTPError("connection failed"))

        with pytest.raises(TokenValidationError, match="introspection request failed"):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_introspect_token_invalid_json(self, oidc_adapter, mock_httpx_client):
        """Invalid JSON in introspection response raises error."""
        oidc_adapter._discovery_cache = {
            "introspection_endpoint": "https://oidc.example.com/oauth/introspect"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(side_effect=json.JSONDecodeError("bad json", "", 0))
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="not valid JSON"):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_introspect_token_missing_sub(self, oidc_adapter, mock_httpx_client):
        """Introspection response missing sub raises error."""
        oidc_adapter._discovery_cache = {
            "introspection_endpoint": "https://oidc.example.com/oauth/introspect"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(return_value={"active": True})
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="missing sub"):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_introspect_token_http_400(self, oidc_adapter, mock_httpx_client):
        """HTTP 400 from introspection endpoint raises error."""
        oidc_adapter._discovery_cache = {
            "introspection_endpoint": "https://oidc.example.com/oauth/introspect"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=400)
        mock_response.json = MagicMock(return_value={})
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="400"):
            await oidc_adapter._introspect_token("token")


class TestUserInfoEndpoint:
    @pytest.mark.asyncio
    async def test_fetch_userinfo_success(self, oidc_adapter, mock_httpx_client):
        """Successful userinfo call returns claims."""
        oidc_adapter._discovery_cache = {
            "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(return_value={"sub": "user-123", "email": "u@example.com"})
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        claims = await oidc_adapter._fetch_userinfo_claims("token")
        assert claims["sub"] == "user-123"

    @pytest.mark.asyncio
    async def test_fetch_userinfo_401(self, oidc_adapter, mock_httpx_client):
        """401 from userinfo raises error."""
        oidc_adapter._discovery_cache = {
            "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=401)
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="401"):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    async def test_fetch_userinfo_missing_endpoint(self, oidc_adapter, mock_httpx_client):
        """Missing userinfo endpoint raises error."""
        oidc_adapter._discovery_cache = {}
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        with pytest.raises(TokenValidationError, match="userinfo endpoint"):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    async def test_fetch_userinfo_http_error(self, oidc_adapter, mock_httpx_client):
        """HTTP error during userinfo call raises error."""
        oidc_adapter._discovery_cache = {
            "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_httpx_client.get = AsyncMock(side_effect=httpx.HTTPError("connection failed"))

        with pytest.raises(TokenValidationError, match="userinfo request failed"):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    async def test_fetch_userinfo_invalid_json(self, oidc_adapter, mock_httpx_client):
        """Invalid JSON from userinfo raises error."""
        oidc_adapter._discovery_cache = {
            "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(side_effect=json.JSONDecodeError("bad", "", 0))
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="not valid JSON"):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    async def test_fetch_userinfo_non_dict(self, oidc_adapter, mock_httpx_client):
        """Non-dict userinfo response raises error."""
        oidc_adapter._discovery_cache = {
            "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo"
        }
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        mock_response = AsyncMock(status_code=200)
        mock_response.json = MagicMock(return_value=["not", "a", "dict"])
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(TokenValidationError, match="invalid shape"):
            await oidc_adapter._fetch_userinfo_claims("token")


class TestExtractUserInfoEdgeCases:
    def test_missing_sub(self, oidc_adapter):
        with pytest.raises(TokenValidationError, match="subject"):
            oidc_adapter.extract_user_info({})

    def test_empty_sub(self, oidc_adapter):
        with pytest.raises(TokenValidationError, match="subject"):
            oidc_adapter.extract_user_info({"sub": ""})

    def test_username_falls_back_to_sub_when_no_email(self, oidc_adapter):
        result = oidc_adapter.extract_user_info({"sub": "user-123"})
        assert result["username"] == "user-123"
        assert result["email"] == "user-123@oidc.local"

    def test_email_falls_back_to_oidc_local(self, oidc_adapter):
        result = oidc_adapter.extract_user_info(
            {
                "sub": "user-456",
                "preferred_username": "jane",
            }
        )
        assert result["email"] == "user-456@oidc.local"

    def test_email_from_username_with_at(self, oidc_adapter):
        result = oidc_adapter.extract_user_info(
            {
                "sub": "user-789",
                "preferred_username": "jane@work.com",
            }
        )
        assert result["email"] == "jane@work.com"


class TestValidateTokenFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_introspection(self, oidc_adapter):
        """When JWT and userinfo fail, should try introspection."""
        oidc_adapter._validate_jwt_token = AsyncMock(side_effect=TokenValidationError("jwt fail"))
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo fail")
        )
        oidc_adapter._introspect_token = AsyncMock(
            return_value={"active": True, "sub": "introspect-user"}
        )

        claims = await oidc_adapter.validate_token("opaque-token")

        assert claims["sub"] == "introspect-user"
        oidc_adapter._introspect_token.assert_called_once_with("opaque-token")

    @pytest.mark.asyncio
    async def test_all_fallbacks_fail(self, oidc_adapter):
        """When all validation paths fail, should raise."""
        oidc_adapter._validate_jwt_token = AsyncMock(side_effect=TokenValidationError("jwt fail"))
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo fail")
        )
        oidc_adapter._introspect_token = AsyncMock(
            side_effect=TokenValidationError("introspect fail")
        )

        with pytest.raises(TokenValidationError, match="JWT validation failed"):
            await oidc_adapter.validate_token("bad-token")


class TestJWKSEdgeCases:
    @pytest.mark.asyncio
    async def test_fetch_jwks_no_uri(self, oidc_adapter, mock_httpx_client):
        """JWKS fetch should fail when jwks_uri is missing."""
        oidc_adapter._discovery_cache = {"issuer": "https://example.com"}
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        with pytest.raises(JWKSFetchError, match="JWKS URI"):
            await oidc_adapter.fetch_jwks()


class TestOIDCClose:
    @pytest.mark.asyncio
    async def test_close(self, oidc_adapter, mock_httpx_client):
        await oidc_adapter.close()
        mock_httpx_client.aclose.assert_awaited_once()
        assert oidc_adapter._httpx_client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self):
        adapter = OIDCAdapter(
            discovery_url="https://example.com",
            client_id="test",
            client_secret="secret",
            httpx_client=None,
        )
        adapter._httpx_client = None
        await adapter.close()  # Should not crash
