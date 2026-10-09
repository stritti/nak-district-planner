"""Authentication API routes.

- GET /api/v1/auth/me — Get current authenticated user info
- GET /api/v1/auth/oidc/discovery — Get OIDC discovery document (proxied from provider)
- POST /api/v1/auth/oidc/token — Proxy token exchange to OIDC provider
- POST /api/v1/auth/oidc/revoke — Revoke the server-held refresh token
- GET /api/v1/auth/access — Get user access context and memberships

RBAC Notes:
- /oidc/discovery: PUBLIC - No auth required (frontend needs before login)
- /oidc/token: PUBLIC - No auth required (OIDC callback / refresh flow)
- /oidc/revoke: PUBLIC but CSRF-protected - clears the browser refresh session
- /me: AUTHENTICATED - Any valid token, no role requirement
- /access: VIEWER - Requires VIEWER role in at least one district
"""

import logging
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, model_validator

from app.adapters.api.deps import (
    AuthenticatedUser,
    RawCurrentUserWithMemberships,
    get_oidc_adapter,
)
from app.adapters.api.schemas.user import AccessContextOut, MembershipOut, UserOut
from app.adapters.auth.oidc import OIDCDiscoveryError
from app.adapters.auth.permissions import get_districts_where_user_has_role
from app.config import settings
from app.domain.models.role import Role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "oidc_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/oidc"


class OIDCTokenExchangeRequest(BaseModel):
    """Browser-safe parameters for an OIDC authorization-code or refresh grant.

    Provider refresh credentials never cross the JavaScript boundary. A refresh
    grant therefore needs only its grant type; the credential is read from the
    HttpOnly refresh-session cookie.
    """

    grant_type: Literal["authorization_code", "refresh_token"] = "authorization_code"
    code: str | None = None
    redirect_uri: str | None = None
    code_verifier: str | None = None

    @model_validator(mode="after")
    def validate_grant_parameters(self) -> OIDCTokenExchangeRequest:
        if self.grant_type == "authorization_code" and (
            not self.code or not self.redirect_uri or not self.code_verifier
        ):
            raise ValueError(
                "Authorization-code grant requires code, redirect_uri, and code_verifier"
            )
        return self


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Store a provider refresh token where frontend JavaScript cannot read it."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Expire the server-held browser refresh session."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _split_token_payload(payload: object) -> tuple[dict, str | None]:
    """Return a browser-safe token payload and an optional provider refresh credential."""
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC token endpoint returned an invalid response",
        )

    sanitized = dict(payload)
    refresh_token = sanitized.pop("refresh_token", None)
    if refresh_token is not None and (not isinstance(refresh_token, str) or not refresh_token):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC token endpoint returned an invalid refresh token",
        )
    return sanitized, refresh_token


def _provider_json(response: httpx.Response) -> object:
    """Parse provider JSON and map malformed success responses to a gateway error."""
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC token endpoint returned invalid JSON",
        ) from exc


@router.get("/oidc/discovery")
async def get_oidc_discovery() -> dict:
    """Return the OIDC discovery document with frontend-facing proxy endpoints."""
    adapter = get_oidc_adapter()
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC adapter not initialized",
        )
    try:
        discovery = await adapter.discover()
        frontend_discovery = {
            **discovery,
            "client_id": adapter.client_id,
        }
        if discovery.get("revocation_endpoint"):
            frontend_discovery["revocation_endpoint"] = "/api/v1/auth/oidc/revoke"
        return frontend_discovery
    except OIDCDiscoveryError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OIDC discovery failed: {e}",
        ) from e


@router.post("/oidc/token")
async def exchange_oidc_token(
    body: OIDCTokenExchangeRequest,
    request: Request,
    response: Response,
) -> dict:
    """Proxy token exchange while retaining refresh credentials server-side."""
    adapter = get_oidc_adapter()
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC adapter not initialized",
        )

    discovery = await adapter.discover()
    token_endpoint = discovery.get("token_endpoint")
    if not token_endpoint:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC discovery missing token_endpoint",
        )

    provider_refresh_token: str | None = None
    data: dict[str, str] = {
        "grant_type": body.grant_type,
        "client_id": adapter.client_id,
        "client_secret": adapter.client_secret,
    }
    if body.grant_type == "authorization_code":
        data.update(
            code=body.code,
            redirect_uri=body.redirect_uri,
            code_verifier=body.code_verifier,
        )
    else:
        provider_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
        if not provider_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "missing_refresh_cookie"},
            )
        data["refresh_token"] = provider_refresh_token

    client = await adapter.get_httpx_client()
    try:
        provider_response = await client.post(token_endpoint, data=data, timeout=15)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token exchange failed: {e}",
        ) from e

    if not provider_response.is_success:
        try:
            provider_detail: dict | str = provider_response.json()
        except ValueError:
            provider_detail = provider_response.text
        raise HTTPException(
            status_code=provider_response.status_code,
            detail=provider_detail or {"error": "token_exchange_failed"},
        )

    payload, rotated_refresh_token = _split_token_payload(_provider_json(provider_response))
    if rotated_refresh_token:
        _set_refresh_cookie(response, rotated_refresh_token)

    # This is session metadata, not a credential or coordination token. During
    # a refresh grant an existing cookie remains valid when the provider does
    # not rotate it.
    payload["refresh_session"] = bool(rotated_refresh_token or provider_refresh_token)
    return payload


@router.post("/oidc/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_oidc_refresh_token(request: Request) -> Response:
    """Best-effort provider revocation followed by unconditional local logout."""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    adapter = get_oidc_adapter()

    try:
        if refresh_token and adapter is not None:
            discovery = await adapter.discover()
            revocation_endpoint = discovery.get("revocation_endpoint")
            if revocation_endpoint:
                client = await adapter.get_httpx_client()
                provider_response = await client.post(
                    revocation_endpoint,
                    data={
                        "token": refresh_token,
                        "token_type_hint": "refresh_token",
                        "client_id": adapter.client_id,
                        "client_secret": adapter.client_secret,
                    },
                    timeout=10,
                )
                provider_response.raise_for_status()
    except (httpx.HTTPError, OIDCDiscoveryError) as exc:
        # Local logout must remain available when the provider is unavailable,
        # but failed provider revocation must stay operationally visible.
        logger.warning("OIDC provider refresh-token revocation failed: %s", exc)

    # Return a real response. FastAPI's injected ``Response`` parameter is only
    # a header carrier whose status code is unset (``None``); sending it as the
    # response crashes uvicorn with ``KeyError: None`` and the proxy answers 502.
    result = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(result)
    return result


@router.get("/me", response_model=UserOut)
async def get_current_user_info(user: AuthenticatedUser) -> UserOut:
    """Get current authenticated user info."""
    return UserOut(
        sub=user.sub,
        email=user.email,
        username=user.username,
        name=user.name,
        given_name=user.given_name,
        family_name=user.family_name,
        is_superadmin=user.is_superadmin,
    )


@router.get("/access", response_model=AccessContextOut)
async def get_access_context(auth: RawCurrentUserWithMemberships) -> AccessContextOut:
    """Return effective memberships for access-aware frontend UX."""
    memberships = [
        MembershipOut(
            role=m.role.value,
            scope_type=m.scope_type.value,
            scope_id=str(m.scope_id),
        )
        for m in auth.memberships
    ]

    if memberships:
        districts_with_viewer = get_districts_where_user_has_role(auth, Role.VIEWER)
        if not districts_with_viewer and not auth.user.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur Benutzer mit VIEWER-Rolle in mindestens einem Bezirk können auf diese Ressource zugreifen.",
            )

    access_status = "ACTIVE" if auth.user.is_superadmin or memberships else "PENDING_APPROVAL"
    return AccessContextOut(status=access_status, memberships=memberships)
