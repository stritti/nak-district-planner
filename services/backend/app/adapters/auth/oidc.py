"""OIDCAdapter — Provider-agnostic OIDC/OAuth2 integration.

Handles OIDC discovery, JWKS fetching/caching, and JWT validation.
Works with any OIDC-compliant provider (Keycloak, Authentik, Okta, etc.)
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
from jwt import PyJWK

logger = logging.getLogger(__name__)


class OIDCDiscoveryError(Exception):
    """Raised when OIDC discovery fails."""

    pass


class JWKSFetchError(Exception):
    """Raised when JWKS fetch fails."""

    pass


class TokenValidationError(Exception):
    """Raised when token validation fails."""

    pass


class OIDCAdapter:
    """Provider-agnostic OIDC adapter for JWT validation and user extraction.

    Features:
    - OIDC discovery: fetches /.well-known/openid-configuration
    - JWKS caching: 1-hour TTL, with fallback to cached keys on fetch errors
    - JWT validation: signature, issuer, expiration, audience claims
    - Error handling: connection errors, invalid tokens, cache miss fallbacks
    """

    def __init__(
        self,
        discovery_url: str,
        client_id: str,
        client_secret: str,
        issuer: str | None = None,
        audience: str | None = None,
        httpx_client: httpx.AsyncClient | None = None,
        jwks_cache_ttl: int = 3600,  # 1 hour
        clock_skew_seconds: int = 120,
    ):
        """Initialize the OIDC adapter.

        Args:
            discovery_url: OIDC provider discovery URL
                          (e.g., https://oidc.example.com/.well-known/openid-configuration)
            client_id: OIDC client ID
            client_secret: OIDC client secret
            issuer: Expected issuer (if not provided, discovered from OIDC config)
            audience: Expected audience for access tokens (defaults to client_id)
            httpx_client: Optional httpx.AsyncClient for testing
            jwks_cache_ttl: JWKS cache time-to-live in seconds
            clock_skew_seconds: Allowed clock skew (exp/nbf/iat leeway)
        """
        self.discovery_url = discovery_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer = issuer
        self.audience = audience
        self.jwks_cache_ttl = jwks_cache_ttl
        self.clock_skew_seconds = clock_skew_seconds

        self._httpx_client = httpx_client
        self._discovery_cache: dict[str, Any] | None = None
        self._discovery_cache_time: datetime | None = None
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_time: datetime | None = None
        self._jwks_fetch_error: Exception | None = None

    async def get_httpx_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient()
        return self._httpx_client

    async def close(self) -> None:
        """Close httpx client if we created it."""
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
            self._httpx_client = None

    async def discover(self) -> dict[str, Any]:
        """Fetch OIDC discovery configuration from /.well-known/openid-configuration.

        Returns:
            Discovery configuration dict with endpoints and metadata

        Raises:
            OIDCDiscoveryError: If discovery fails
        """
        # Return cached discovery if fresh
        if self._discovery_cache is not None and self._discovery_cache_time is not None:
            elapsed = (datetime.now(UTC) - self._discovery_cache_time).total_seconds()
            if elapsed < 3600:  # Cache for 1 hour
                return self._discovery_cache

        try:
            client = await self.get_httpx_client()
            response = await client.get(self.discovery_url, timeout=10)
            response.raise_for_status()

            self._discovery_cache = response.json()
            self._discovery_cache_time = datetime.now(UTC)

            # Auto-discover issuer if not provided
            if self.issuer is None and "issuer" in self._discovery_cache:
                self.issuer = self._discovery_cache["issuer"]

            logger.info(f"OIDC discovery successful: issuer={self.issuer}")
            return self._discovery_cache

        except httpx.HTTPError as e:
            msg = f"OIDC discovery failed: {e}"
            logger.error(msg)
            raise OIDCDiscoveryError(msg) from e
        except (json.JSONDecodeError, KeyError) as e:
            msg = f"OIDC discovery: invalid response: {e}"
            logger.error(msg)
            raise OIDCDiscoveryError(msg) from e

    async def fetch_jwks(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch and cache JWKS (JSON Web Key Set) from the OIDC provider.

        Returns:
            JWKS dict with 'keys' array

        Raises:
            JWKSFetchError: If fetch fails and no cached keys available
        """
        # Return cached JWKS if fresh and not forcing refresh
        if not force_refresh and self._jwks_cache is not None and self._jwks_cache_time is not None:
            elapsed = (datetime.now(UTC) - self._jwks_cache_time).total_seconds()
            if elapsed < self.jwks_cache_ttl:
                return self._jwks_cache

        try:
            discovery = await self.discover()
            jwks_uri = discovery.get("jwks_uri")

            if not jwks_uri:
                raise JWKSFetchError("JWKS URI not found in discovery configuration")

            client = await self.get_httpx_client()
            response = await client.get(jwks_uri, timeout=10)
            response.raise_for_status()

            self._jwks_cache = response.json()
            self._jwks_cache_time = datetime.now(UTC)
            self._jwks_fetch_error = None

            logger.info(f"JWKS fetched successfully, {len(self._jwks_cache.get('keys', []))} keys")
            return self._jwks_cache

        except httpx.HTTPError as e:
            msg = f"JWKS fetch failed: {e}"
            logger.error(msg)
            self._jwks_fetch_error = e

            # Fallback: return cached JWKS if available, even if stale
            if self._jwks_cache is not None:
                logger.warning(f"Using stale JWKS cache (last updated: {self._jwks_cache_time})")
                return self._jwks_cache

            raise JWKSFetchError(msg) from e
        except (json.JSONDecodeError, KeyError) as e:
            msg = f"JWKS: invalid response: {e}"
            logger.error(msg)
            self._jwks_fetch_error = e

            # Fallback: return cached JWKS if available
            if self._jwks_cache is not None:
                logger.warning("Using stale JWKS cache due to parse error")
                return self._jwks_cache

            raise JWKSFetchError(msg) from e

    async def validate_token(
        self,
        token: str,
        audience: str | None = None,
        algorithms: list[str] | None = None,
    ) -> dict[str, Any]:
        """Validate JWT token: signature, issuer, expiration, audience.

        Args:
            token: JWT token to validate
            audience: Expected audience claim (typically client_id)
            algorithms: Allowed signing algorithms (default: ['RS256', 'HS256'])

        Returns:
            Decoded token claims dict

        Raises:
            TokenValidationError: If token is invalid or expired
        """
        if algorithms is None:
            algorithms = ["RS256", "HS256"]

        jwt_validation_error: TokenValidationError | None = None

        try:
            return await self._validate_jwt_token(
                token=token,
                audience=audience,
                algorithms=algorithms,
            )
        except TokenValidationError as e:
            jwt_validation_error = e
            logger.info(f"JWT token validation failed, trying userinfo fallback: {e}")

        # Standards-compatible fallback for opaque access tokens:
        # validate token by calling provider's userinfo endpoint.
        try:
            userinfo_claims = await self._fetch_userinfo_claims(token)
            logger.info(
                "Token validated through userinfo endpoint for user: %s",
                userinfo_claims.get("sub"),
            )
            return userinfo_claims
        except TokenValidationError as e:
            logger.info(f"userinfo validation failed, trying introspection fallback: {e}")
            userinfo_validation_error = e

        # RFC 7662 fallback for opaque tokens:
        # validate token by using provider introspection endpoint.
        try:
            introspection_claims = await self._introspect_token(token)
            logger.info(
                "Token validated through introspection endpoint for user: %s",
                introspection_claims.get("sub"),
            )
            return introspection_claims
        except TokenValidationError as e:
            if jwt_validation_error:
                raise TokenValidationError(
                    "JWT validation failed "
                    f"({jwt_validation_error}); userinfo validation failed ({userinfo_validation_error}); "
                    f"introspection validation failed ({e})"
                ) from e
            raise
        except Exception as e:
            if jwt_validation_error:
                raise TokenValidationError(
                    "JWT validation failed "
                    f"({jwt_validation_error}); userinfo validation failed ({userinfo_validation_error}); "
                    f"introspection validation failed ({e})"
                ) from e
            raise TokenValidationError(f"Token validation failed: {e}") from e

    async def _validate_jwt_token(
        self,
        token: str,
        audience: str | None,
        algorithms: list[str],
    ) -> dict[str, Any]:
        """Validate JWT token via JWKS (signature + standard claims)."""
        try:
            # Decode header to get kid (key ID) without verifying first
            unverified = jwt.decode(token, options={"verify_signature": False})
            header = jwt.get_unverified_header(token)

            logger.debug(f"Token header: {header}")
            logger.debug(f"Token claims: {unverified}")

            # Validate issuer
            if self.issuer and unverified.get("iss") != self.issuer:
                raise TokenValidationError(
                    f"Invalid issuer: {unverified.get('iss')} (expected {self.issuer})"
                )

            # Fetch JWKS to get the signing key
            jwks = await self.fetch_jwks()
            keys = jwks.get("keys", [])

            if not keys:
                raise TokenValidationError("No keys available in JWKS")

            # Find the key by kid
            kid = header.get("kid")
            signing_key = None

            for key_data in keys:
                if key_data.get("kid") == kid:
                    signing_key = key_data
                    break

            if not signing_key:
                logger.warning(f"Key ID {kid} not found in JWKS, trying force refresh")
                # Try refreshing JWKS in case keys were rotated
                jwks = await self.fetch_jwks(force_refresh=True)
                keys = jwks.get("keys", [])

                for key_data in keys:
                    if key_data.get("kid") == kid:
                        signing_key = key_data
                        break

            if not signing_key:
                raise TokenValidationError(f"Signing key not found for kid: {kid}")

            # Build the public key from JWKS entry using PyJWK
            try:
                pyjwk = PyJWK(signing_key, algorithm=header.get("alg"))
                signing_key_obj = pyjwk.key
            except Exception as e:
                raise TokenValidationError(f"Failed to build signing key from JWKS: {e}") from e

            # Verify signature and claims
            decoded = jwt.decode(
                token,
                signing_key_obj,
                algorithms=algorithms,
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={
                    "verify_signature": True,
                    "verify_aud": False,
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )

            expected_audience = audience or self.audience or self.client_id
            self._validate_audience_claims(decoded, expected_audience)

            logger.info(f"Token validated successfully for user: {decoded.get('sub')}")
            return decoded

        except jwt.DecodeError as e:
            raise TokenValidationError(f"Token decode error: {e}") from e
        except jwt.ExpiredSignatureError as e:
            raise TokenValidationError(f"Token expired: {e}") from e
        except jwt.InvalidTokenError as e:
            raise TokenValidationError(f"Invalid token: {e}") from e
        except Exception as e:
            # Catch-all for unexpected errors
            raise TokenValidationError(f"Token validation failed: {e}") from e

    async def _fetch_userinfo_claims(self, token: str) -> dict[str, Any]:
        """Validate access token by calling the OIDC userinfo endpoint."""
        discovery = await self.discover()
        userinfo_endpoint = discovery.get("userinfo_endpoint")
        if not userinfo_endpoint:
            raise TokenValidationError("userinfo endpoint not available in discovery")

        client = await self.get_httpx_client()
        try:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
        except httpx.HTTPError as e:
            raise TokenValidationError(f"userinfo request failed: {e}") from e

        if response.status_code == 401:
            raise TokenValidationError("userinfo rejected token (401)")
        if response.status_code >= 400:
            raise TokenValidationError(
                f"userinfo request failed with status {response.status_code}"
            )

        try:
            claims = response.json()
        except json.JSONDecodeError as e:
            raise TokenValidationError("userinfo response is not valid JSON") from e

        if not isinstance(claims, dict):
            raise TokenValidationError("userinfo response has invalid shape")
        if not claims.get("sub"):
            raise TokenValidationError("userinfo response missing sub claim")

        return claims

    async def _introspect_token(self, token: str) -> dict[str, Any]:
        """Validate opaque access token via RFC 7662 introspection."""
        discovery = await self.discover()
        introspection_endpoint = discovery.get("introspection_endpoint")
        if not introspection_endpoint:
            raise TokenValidationError("introspection endpoint not available in discovery")

        client = await self.get_httpx_client()
        body = {
            "token": token,
            "token_type_hint": "access_token",
        }

        try:
            response = await client.post(
                introspection_endpoint,
                data=body,
                auth=(self.client_id, self.client_secret),
                timeout=10,
            )
        except httpx.HTTPError as e:
            raise TokenValidationError(f"introspection request failed: {e}") from e

        if response.status_code >= 400:
            raise TokenValidationError(
                f"introspection request failed with status {response.status_code}"
            )

        try:
            claims = response.json()
        except json.JSONDecodeError as e:
            raise TokenValidationError("introspection response is not valid JSON") from e

        if not isinstance(claims, dict):
            raise TokenValidationError("introspection response has invalid shape")
        if not claims.get("active"):
            raise TokenValidationError("introspection marks token as inactive")
        if not claims.get("sub"):
            raise TokenValidationError("introspection response missing sub claim")

        return claims

    def _validate_audience_claims(self, token_claims: dict[str, Any], expected: str) -> None:
        """Validate token audience in a provider-compatible way.

        Standards background:
        - access token audience is usually checked via `aud`
        - ID Tokens can include multiple audiences and use `azp` as authorized party

        We accept the token if either:
        - `aud` contains the expected audience (string or list)
        - `azp` matches the expected audience
        """
        aud_claim = token_claims.get("aud")
        azp_claim = token_claims.get("azp")

        aud_matches = False
        if isinstance(aud_claim, str):
            aud_matches = aud_claim == expected
        elif isinstance(aud_claim, list):
            aud_matches = expected in aud_claim

        azp_matches = isinstance(azp_claim, str) and azp_claim == expected

        if not aud_matches and not azp_matches:
            raise TokenValidationError(
                f"Invalid audience: aud={aud_claim!r}, azp={azp_claim!r} (expected {expected!r})"
            )

    def extract_user_info(self, token_claims: dict[str, Any]) -> dict[str, Any]:
        """Extract user information from validated token claims.

        Extracts standard OIDC claims:
        - sub: Subject (user ID)
        - email: Email address
        - preferred_username: Username (falls back to email)
        - given_name, family_name: User name components

        Args:
            token_claims: Decoded JWT claims dict

        Returns:
            User info dict with keys: sub, email, username, name, ...
        """
        sub = token_claims.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise TokenValidationError("Token missing required subject (sub)")

        raw_email = token_claims.get("email")
        raw_username = token_claims.get("preferred_username")

        email = raw_email if isinstance(raw_email, str) and raw_email.strip() else None
        username = raw_username if isinstance(raw_username, str) and raw_username.strip() else None

        if username is None:
            username = email or sub

        if email is None:
            email = username if "@" in username else f"{sub}@oidc.local"

        return {
            "sub": sub,
            "email": email,
            "username": username,
            "name": token_claims.get("name") or token_claims.get("given_name", ""),
            "given_name": token_claims.get("given_name"),
            "family_name": token_claims.get("family_name"),
        }
