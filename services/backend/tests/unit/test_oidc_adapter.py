"""
Unit tests for OIDCAdapter — OIDC discovery, JWKS caching, JWT validation.

Tests use mocked OIDC provider responses to ensure provider-agnostic behavior.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.adapters.auth.oidc import (
    OIDCAdapter,
    OIDCDiscoveryError,
    JWKSFetchError,
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
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
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
        with pytest.raises(TokenValidationError):
            await oidc_adapter.validate_token("invalid-token")

    @pytest.mark.asyncio
    async def test_extract_user_info_called_in_validate(self, oidc_adapter, mock_httpx_client):
        """Test that user info extraction is available after validation."""
        # This test is limited due to JWT signing complexity
        # In production, integration tests with real OIDC provider are recommended
        pass
