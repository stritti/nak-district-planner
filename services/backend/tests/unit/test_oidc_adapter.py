# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for the provider-agnostic OIDC adapter.

The response doubles intentionally use ``MagicMock`` because httpx response
methods such as ``raise_for_status()`` and ``json()`` are synchronous. This
keeps the tests aligned with the real httpx API and avoids un-awaited coroutine
warnings from overly broad ``AsyncMock`` response objects.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest

from app.adapters.auth.oidc import (
    JWKSFetchError,
    OIDCAdapter,
    OIDCDiscoveryError,
    TokenValidationError,
)

MOCK_DISCOVERY = {
    "issuer": "https://oidc.example.com",
    "authorization_endpoint": "https://oidc.example.com/oauth/authorize",
    "token_endpoint": "https://oidc.example.com/oauth/token",
    "userinfo_endpoint": "https://oidc.example.com/oauth/userinfo",
    "introspection_endpoint": "https://oidc.example.com/oauth/introspect",
    "jwks_uri": "https://oidc.example.com/oauth/certs",
}

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


def response(*, status_code: int = 200, payload: object | None = None) -> MagicMock:
    """Create a response double matching httpx's synchronous response API."""
    result = MagicMock(spec=httpx.Response)
    result.status_code = status_code
    result.json.return_value = payload
    result.raise_for_status.return_value = None
    return result


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def oidc_adapter(mock_httpx_client: AsyncMock) -> OIDCAdapter:
    return OIDCAdapter(
        discovery_url="https://oidc.example.com/.well-known/openid-configuration",
        client_id="test-client",
        client_secret="test-secret",
        issuer="https://oidc.example.com",
        httpx_client=mock_httpx_client,
    )


class TestOIDCDiscovery:
    @pytest.mark.asyncio
    async def test_discover_success_and_cache(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        mock_httpx_client.get.return_value = response(payload=MOCK_DISCOVERY)

        first = await oidc_adapter.discover()
        second = await oidc_adapter.discover()

        assert first == MOCK_DISCOVERY
        assert second == MOCK_DISCOVERY
        mock_httpx_client.get.assert_awaited_once_with(
            "https://oidc.example.com/.well-known/openid-configuration",
            timeout=10,
        )

    @pytest.mark.asyncio
    async def test_discover_http_error(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        mock_httpx_client.get.side_effect = httpx.ConnectError("connection failed")

        with pytest.raises(OIDCDiscoveryError, match="discovery failed"):
            await oidc_adapter.discover()

    @pytest.mark.asyncio
    async def test_discover_invalid_json(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        invalid = response(payload={})
        invalid.json.side_effect = json.JSONDecodeError("bad", "", 0)
        mock_httpx_client.get.return_value = invalid

        with pytest.raises(OIDCDiscoveryError, match="invalid response"):
            await oidc_adapter.discover()


class TestJWKSFetching:
    @pytest.mark.asyncio
    async def test_fetch_jwks_success_and_cache(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        oidc_adapter._discovery_cache = MOCK_DISCOVERY
        oidc_adapter._discovery_cache_time = datetime.now(UTC)
        mock_httpx_client.get.return_value = response(payload=MOCK_JWKS)

        first = await oidc_adapter.fetch_jwks()
        second = await oidc_adapter.fetch_jwks()

        assert first == MOCK_JWKS
        assert second == MOCK_JWKS
        mock_httpx_client.get.assert_awaited_once_with(
            MOCK_DISCOVERY["jwks_uri"],
            timeout=10,
        )

    @pytest.mark.asyncio
    async def test_fetch_jwks_uses_stale_cache_on_transport_error(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        oidc_adapter._jwks_cache = MOCK_JWKS
        oidc_adapter._jwks_cache_time = datetime.now(UTC) - timedelta(hours=2)
        oidc_adapter._discovery_cache = MOCK_DISCOVERY
        oidc_adapter._discovery_cache_time = datetime.now(UTC)
        mock_httpx_client.get.side_effect = httpx.ConnectError("offline")

        assert await oidc_adapter.fetch_jwks(force_refresh=True) == MOCK_JWKS

    @pytest.mark.asyncio
    async def test_fetch_jwks_uses_stale_cache_on_parse_error(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        oidc_adapter._jwks_cache = MOCK_JWKS
        oidc_adapter._jwks_cache_time = datetime.now(UTC) - timedelta(hours=2)
        oidc_adapter._discovery_cache = MOCK_DISCOVERY
        oidc_adapter._discovery_cache_time = datetime.now(UTC)
        invalid = response(payload={})
        invalid.json.side_effect = json.JSONDecodeError("bad", "", 0)
        mock_httpx_client.get.return_value = invalid

        assert await oidc_adapter.fetch_jwks(force_refresh=True) == MOCK_JWKS

    @pytest.mark.asyncio
    async def test_fetch_jwks_without_cache_propagates_transport_error(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        oidc_adapter._discovery_cache = MOCK_DISCOVERY
        oidc_adapter._discovery_cache_time = datetime.now(UTC)
        mock_httpx_client.get.side_effect = httpx.ConnectError("offline")

        with pytest.raises(JWKSFetchError, match="fetch failed"):
            await oidc_adapter.fetch_jwks()

    @pytest.mark.asyncio
    async def test_fetch_jwks_requires_uri(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._discovery_cache = {"issuer": "https://oidc.example.com"}
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

        with pytest.raises(JWKSFetchError, match="JWKS URI"):
            await oidc_adapter.fetch_jwks()


class TestTokenClassificationAndFallback:
    @pytest.mark.asyncio
    async def test_opaque_token_requires_client_bound_introspection_before_userinfo(
        self,
        oidc_adapter: OIDCAdapter,
    ) -> None:
        oidc_adapter._validate_jwt_token = AsyncMock()
        oidc_adapter._introspect_token = AsyncMock(
            return_value={"active": True, "sub": "opaque-user", "client_id": "test-client"}
        )
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            return_value={"sub": "opaque-user", "iss": "https://oidc.example.com"}
        )

        claims = await oidc_adapter.validate_token("opaque-access-token")

        assert claims["sub"] == "opaque-user"
        oidc_adapter._validate_jwt_token.assert_not_awaited()
        oidc_adapter._introspect_token.assert_awaited_once_with("opaque-access-token")
        oidc_adapter._fetch_userinfo_claims.assert_awaited_once_with("opaque-access-token")

    @pytest.mark.asyncio
    async def test_opaque_token_uses_introspection_when_userinfo_fails(
        self,
        oidc_adapter: OIDCAdapter,
    ) -> None:
        oidc_adapter._validate_jwt_token = AsyncMock()
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo unavailable")
        )
        oidc_adapter._introspect_token = AsyncMock(
            return_value={
                "active": True,
                "sub": "introspected-user",
                "client_id": "test-client",
            }
        )

        claims = await oidc_adapter.validate_token("opaque-access-token")

        assert claims["sub"] == "introspected-user"
        oidc_adapter._validate_jwt_token.assert_not_awaited()
        oidc_adapter._introspect_token.assert_awaited_once_with("opaque-access-token")

    @pytest.mark.asyncio
    async def test_all_opaque_validation_paths_fail_closed(
        self,
        oidc_adapter: OIDCAdapter,
    ) -> None:
        oidc_adapter._validate_jwt_token = AsyncMock()
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo fail")
        )
        oidc_adapter._introspect_token = AsyncMock(
            side_effect=TokenValidationError("introspection fail")
        )

        with pytest.raises(TokenValidationError, match="introspection fail"):
            await oidc_adapter.validate_token("bad-token")

        oidc_adapter._validate_jwt_token.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unexpected_introspection_failure_is_not_wrapped(
        self,
        oidc_adapter: OIDCAdapter,
    ) -> None:
        oidc_adapter._fetch_userinfo_claims = AsyncMock(
            side_effect=TokenValidationError("userinfo fail")
        )
        oidc_adapter._introspect_token = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            await oidc_adapter.validate_token("opaque-token")


class TestOpaqueClaimValidation:
    def test_matching_client_and_audience_are_accepted(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._validate_opaque_claims(
            {
                "sub": "user",
                "iss": "https://oidc.example.com",
                "client_id": "test-client",
                "aud": ["test-client"],
            },
            "test-client",
        )

    def test_wrong_issuer_is_rejected(self, oidc_adapter: OIDCAdapter) -> None:
        with pytest.raises(TokenValidationError, match="Invalid issuer"):
            oidc_adapter._validate_opaque_claims(
                {"sub": "user", "iss": "https://other.example.com"},
                "test-client",
            )

    def test_wrong_client_is_rejected(self, oidc_adapter: OIDCAdapter) -> None:
        with pytest.raises(TokenValidationError, match="Invalid client_id"):
            oidc_adapter._validate_opaque_claims(
                {"sub": "user", "client_id": "other-client"},
                "test-client",
            )

    def test_wrong_audience_is_rejected(self, oidc_adapter: OIDCAdapter) -> None:
        with pytest.raises(TokenValidationError, match="Invalid audience"):
            oidc_adapter._validate_opaque_claims(
                {"sub": "user", "aud": ["other-api"]},
                "test-client",
            )


class TestAudienceValidation:
    def test_accepts_string_audience(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._validate_audience_claims({"aud": "test-client"}, "test-client")

    def test_accepts_list_audience(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._validate_audience_claims(
            {"aud": ["other", "test-client"]},
            "test-client",
        )

    def test_accepts_azp_when_aud_is_absent(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._validate_audience_claims(
            {"azp": "test-client"},
            "test-client",
        )

    def test_rejects_no_match(self, oidc_adapter: OIDCAdapter) -> None:
        with pytest.raises(TokenValidationError, match="Invalid audience"):
            oidc_adapter._validate_audience_claims(
                {"aud": ["other"], "azp": "other"},
                "test-client",
            )


class TestJWTValidationInternal:
    fake_token = (
        "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3Qta2V5LWlkIn0."
        "eyJzdWIiOiJ1c2VyMTIzIiwiaXNzIjoiaHR0cHM6Ly9vaWRjLmV4YW1wbGUuY29tIn0."
        "fakesig"
    )

    @pytest.mark.asyncio
    async def test_rejects_wrong_unverified_issuer(self, oidc_adapter: OIDCAdapter) -> None:
        with patch(
            "app.adapters.auth.oidc.jwt.decode",
            return_value={"iss": "https://wrong.example.com"},
        ):
            with pytest.raises(TokenValidationError, match="Invalid issuer"):
                await oidc_adapter._validate_jwt_token(
                    self.fake_token,
                    audience="test-client",
                    algorithms=["RS256"],
                )

    @pytest.mark.asyncio
    async def test_rejects_empty_jwks(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter.fetch_jwks = AsyncMock(return_value={"keys": []})
        with patch(
            "app.adapters.auth.oidc.jwt.decode",
            return_value={"iss": "https://oidc.example.com"},
        ), patch(
            "app.adapters.auth.oidc.jwt.get_unverified_header",
            return_value={"alg": "RS256", "kid": "test-key-id"},
        ):
            with pytest.raises(TokenValidationError, match="No keys"):
                await oidc_adapter._validate_jwt_token(
                    self.fake_token,
                    audience="test-client",
                    algorithms=["RS256"],
                )

    @pytest.mark.asyncio
    async def test_refreshes_unknown_kid_then_rejects(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter.fetch_jwks = AsyncMock(return_value=MOCK_JWKS)
        with patch(
            "app.adapters.auth.oidc.jwt.decode",
            return_value={"iss": "https://oidc.example.com"},
        ), patch(
            "app.adapters.auth.oidc.jwt.get_unverified_header",
            return_value={"alg": "RS256", "kid": "unknown"},
        ):
            with pytest.raises(TokenValidationError, match="Signing key not found"):
                await oidc_adapter._validate_jwt_token(
                    self.fake_token,
                    audience="test-client",
                    algorithms=["RS256"],
                )

        assert oidc_adapter.fetch_jwks.await_count == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error", "message"),
        [
            (jwt.DecodeError("bad"), "decode"),
            (jwt.ExpiredSignatureError("expired"), "expired"),
            (jwt.InvalidTokenError("invalid"), "Invalid token"),
        ],
    )
    async def test_maps_token_decode_errors(
        self,
        oidc_adapter: OIDCAdapter,
        error: Exception,
        message: str,
    ) -> None:
        oidc_adapter.fetch_jwks = AsyncMock(return_value=MOCK_JWKS)

        def decode(token: str, key: object = None, **kwargs: object) -> dict:
            if kwargs.get("options") == {"verify_signature": False}:
                return {"iss": "https://oidc.example.com", "sub": "user"}
            raise error

        with patch("app.adapters.auth.oidc.jwt.decode", side_effect=decode), patch(
            "app.adapters.auth.oidc.jwt.get_unverified_header",
            return_value={"alg": "RS256", "kid": "test-key-id"},
        ):
            with pytest.raises(TokenValidationError, match=message):
                await oidc_adapter._validate_jwt_token(
                    self.fake_token,
                    audience="test-client",
                    algorithms=["RS256"],
                )

    @pytest.mark.asyncio
    async def test_unexpected_decode_failure_is_not_wrapped(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter.fetch_jwks = AsyncMock(return_value=MOCK_JWKS)

        def decode(token: str, key: object = None, **kwargs: object) -> dict:
            if kwargs.get("options") == {"verify_signature": False}:
                return {"iss": "https://oidc.example.com", "sub": "user"}
            raise ValueError("unexpected")

        with patch("app.adapters.auth.oidc.jwt.decode", side_effect=decode), patch(
            "app.adapters.auth.oidc.jwt.get_unverified_header",
            return_value={"alg": "RS256", "kid": "test-key-id"},
        ):
            with pytest.raises(ValueError, match="unexpected"):
                await oidc_adapter._validate_jwt_token(
                    self.fake_token,
                    audience="test-client",
                    algorithms=["RS256"],
                )


class TestUserInfo:
    def prepare(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._discovery_cache = MOCK_DISCOVERY
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_success(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.get.return_value = response(
            payload={"sub": "user", "email": "user@example.com"}
        )

        claims = await oidc_adapter._fetch_userinfo_claims("token")

        assert claims["sub"] == "user"
        mock_httpx_client.get.assert_awaited_once_with(
            MOCK_DISCOVERY["userinfo_endpoint"],
            headers={"Authorization": "Bearer token"},
            timeout=10,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [401, 500])
    async def test_http_status_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
        status_code: int,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.get.return_value = response(status_code=status_code, payload={})

        with pytest.raises(TokenValidationError, match=str(status_code)):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    async def test_transport_error_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.get.side_effect = httpx.ConnectError("offline")

        with pytest.raises(TokenValidationError, match="request failed"):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            (["not", "a", "dict"], "invalid shape"),
            ({"email": "missing@example.com"}, "missing sub"),
        ],
    )
    async def test_invalid_payload_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
        payload: object,
        message: str,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.get.return_value = response(payload=payload)

        with pytest.raises(TokenValidationError, match=message):
            await oidc_adapter._fetch_userinfo_claims("token")

    @pytest.mark.asyncio
    async def test_invalid_json_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        invalid = response(payload={})
        invalid.json.side_effect = json.JSONDecodeError("bad", "", 0)
        mock_httpx_client.get.return_value = invalid

        with pytest.raises(TokenValidationError, match="not valid JSON"):
            await oidc_adapter._fetch_userinfo_claims("token")


class TestIntrospection:
    def prepare(self, oidc_adapter: OIDCAdapter) -> None:
        oidc_adapter._discovery_cache = MOCK_DISCOVERY
        oidc_adapter._discovery_cache_time = datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_success(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.post.return_value = response(
            payload={"active": True, "sub": "user", "client_id": "test-client"}
        )

        claims = await oidc_adapter._introspect_token("token")

        assert claims["sub"] == "user"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            ({"active": False}, "inactive"),
            ({"active": True}, "missing sub"),
            (["invalid"], "invalid shape"),
        ],
    )
    async def test_invalid_payload_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
        payload: object,
        message: str,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.post.return_value = response(payload=payload)

        with pytest.raises(TokenValidationError, match=message):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_http_error_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.post.return_value = response(status_code=400, payload={})

        with pytest.raises(TokenValidationError, match="400"):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_transport_error_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        mock_httpx_client.post.side_effect = httpx.ConnectError("offline")

        with pytest.raises(TokenValidationError, match="request failed"):
            await oidc_adapter._introspect_token("token")

    @pytest.mark.asyncio
    async def test_invalid_json_is_rejected(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        self.prepare(oidc_adapter)
        invalid = response(payload={})
        invalid.json.side_effect = json.JSONDecodeError("bad", "", 0)
        mock_httpx_client.post.return_value = invalid

        with pytest.raises(TokenValidationError, match="not valid JSON"):
            await oidc_adapter._introspect_token("token")


class TestUserExtraction:
    def test_full_user(self, oidc_adapter: OIDCAdapter) -> None:
        user = oidc_adapter.extract_user_info(
            {
                "sub": "user-1",
                "email": "user@example.com",
                "preferred_username": "tester",
                "name": "Test User",
                "given_name": "Test",
                "family_name": "User",
            }
        )

        assert user["sub"] == "user-1"
        assert user["email"] == "user@example.com"
        assert user["username"] == "tester"
        assert user["name"] == "Test User"

    def test_falls_back_to_subject(self, oidc_adapter: OIDCAdapter) -> None:
        user = oidc_adapter.extract_user_info({"sub": "user-2"})

        assert user["username"] == "user-2"
        assert user["email"] == "user-2@oidc.local"

    def test_rejects_missing_subject(self, oidc_adapter: OIDCAdapter) -> None:
        with pytest.raises(TokenValidationError, match="subject"):
            oidc_adapter.extract_user_info({})

    # Issue #461: only an IdP-asserted, verified ``email`` claim may be used
    # for registration auto-linking.
    def test_email_verified_true_boolean(self, oidc_adapter: OIDCAdapter) -> None:
        user = oidc_adapter.extract_user_info(
            {"sub": "u", "email": "u@example.com", "email_verified": True}
        )
        assert user["email_verified"] is True

    @pytest.mark.parametrize("verified", [None, False, "true", "True", 1, "yes"])
    def test_email_verified_requires_boolean_true(
        self, oidc_adapter: OIDCAdapter, verified: object
    ) -> None:
        claims: dict[str, object] = {"sub": "u", "email": "u@example.com"}
        if verified is not None:
            claims["email_verified"] = verified
        user = oidc_adapter.extract_user_info(claims)
        assert user["email_verified"] is False

    def test_username_fallback_is_never_verified(self, oidc_adapter: OIDCAdapter) -> None:
        user = oidc_adapter.extract_user_info(
            {"sub": "u", "preferred_username": "victim@example.com", "email_verified": True}
        )
        # Display fallback is kept ...
        assert user["email"] == "victim@example.com"
        # ... but it is not a verified email and must not be used for linking.
        assert user["email_verified"] is False


class TestClientLifecycle:
    @pytest.mark.asyncio
    async def test_close_injected_client(
        self,
        oidc_adapter: OIDCAdapter,
        mock_httpx_client: AsyncMock,
    ) -> None:
        await oidc_adapter.close()

        mock_httpx_client.aclose.assert_awaited_once()
        assert oidc_adapter._httpx_client is None

    @pytest.mark.asyncio
    async def test_lazy_client_is_created_and_closed(self) -> None:
        adapter = OIDCAdapter(
            discovery_url="https://oidc.example.com/.well-known/openid-configuration",
            client_id="test-client",
            client_secret="secret",
        )

        client = await adapter.get_httpx_client()
        assert isinstance(client, httpx.AsyncClient)
        await adapter.close()
