"""
OIDCAdapter — Provider-agnostic OIDC/OAuth2 integration.

Handles OIDC discovery, JWKS fetching/caching, and JWT validation.
Works with any OIDC-compliant provider (Keycloak, Authentik, Okta, etc.)
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import jwt
from authlib.jose import JsonWebKey, JsonWebSignature
from authlib.jose.errors import JoseError, InvalidKeyError

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
    """
    Provider-agnostic OIDC adapter for JWT validation and user extraction.

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
        issuer: Optional[str] = None,
        httpx_client: Optional[httpx.AsyncClient] = None,
        jwks_cache_ttl: int = 3600,  # 1 hour
    ):
        """
        Initialize the OIDC adapter.

        Args:
            discovery_url: OIDC provider discovery URL
                          (e.g., https://oidc.example.com/.well-known/openid-configuration)
            client_id: OIDC client ID
            client_secret: OIDC client secret
            issuer: Expected issuer (if not provided, discovered from OIDC config)
            httpx_client: Optional httpx.AsyncClient for testing
            jwks_cache_ttl: JWKS cache time-to-live in seconds
        """
        self.discovery_url = discovery_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer = issuer
        self.jwks_cache_ttl = jwks_cache_ttl

        self._httpx_client = httpx_client
        self._discovery_cache: Optional[dict[str, Any]] = None
        self._discovery_cache_time: Optional[datetime] = None
        self._jwks_cache: Optional[dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._jwks_fetch_error: Optional[Exception] = None

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
        """
        Fetch OIDC discovery configuration from /.well-known/openid-configuration.

        Returns:
            Discovery configuration dict with endpoints and metadata

        Raises:
            OIDCDiscoveryError: If discovery fails
        """
        # Return cached discovery if fresh
        if self._discovery_cache is not None and self._discovery_cache_time is not None:
            elapsed = (datetime.now(timezone.utc) - self._discovery_cache_time).total_seconds()
            if elapsed < 3600:  # Cache for 1 hour
                return self._discovery_cache

        try:
            client = await self.get_httpx_client()
            response = await client.get(self.discovery_url, timeout=10)
            response.raise_for_status()

            self._discovery_cache = response.json()
            self._discovery_cache_time = datetime.now(timezone.utc)

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
        """
        Fetch and cache JWKS (JSON Web Key Set) from the OIDC provider.

        Returns:
            JWKS dict with 'keys' array

        Raises:
            JWKSFetchError: If fetch fails and no cached keys available
        """
        # Return cached JWKS if fresh and not forcing refresh
        if not force_refresh and self._jwks_cache is not None and self._jwks_cache_time is not None:
            elapsed = (datetime.now(timezone.utc) - self._jwks_cache_time).total_seconds()
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
            self._jwks_cache_time = datetime.now(timezone.utc)
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
                logger.warning(f"Using stale JWKS cache due to parse error")
                return self._jwks_cache

            raise JWKSFetchError(msg) from e

    async def validate_token(
        self,
        token: str,
        audience: Optional[str] = None,
        algorithms: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Validate JWT token: signature, issuer, expiration, audience.

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

            # Build the public key from JWKS entry
            try:
                jws = JsonWebSignature()
                public_key = jws.deserialize(token, signing_key)
            except (JoseError, InvalidKeyError) as e:
                raise TokenValidationError(f"Failed to deserialize key: {e}") from e

            # Verify signature and claims
            decoded = jwt.decode(
                token,
                json.dumps(signing_key),  # jwk as json string
                algorithms=algorithms,
                audience=audience or self.client_id,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )

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

    def extract_user_info(self, token_claims: dict[str, Any]) -> dict[str, Any]:
        """
        Extract user information from validated token claims.

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
        return {
            "sub": token_claims.get("sub"),
            "email": token_claims.get("email"),
            "username": token_claims.get("preferred_username") or token_claims.get("email"),
            "name": token_claims.get("name") or token_claims.get("given_name", ""),
            "given_name": token_claims.get("given_name"),
            "family_name": token_claims.get("family_name"),
        }
