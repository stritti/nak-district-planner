"""Authentication API routes.

- GET /api/v1/auth/me — Get current authenticated user info
- GET /api/v1/auth/oidc/discovery — Get OIDC discovery document (proxied from provider)
- POST /api/v1/auth/oidc/token — Proxy token exchange to OIDC provider
- GET /api/v1/auth/access — Get user access context and memberships

RBAC Notes:
- /oidc/discovery: PUBLIC - No auth required (frontend needs before login)
- /oidc/token: PUBLIC - No auth required (OIDC callback flow)
- /me: AUTHENTICATED - Any valid token, no role requirement
- /access: VIEWER - Requires VIEWER role in at least one district
"""

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.adapters.api.deps import (
    AuthenticatedUser,
    RawCurrentUserWithMemberships,
    get_oidc_adapter,
)
from app.adapters.api.schemas.user import AccessContextOut, MembershipOut, UserOut
from app.adapters.auth.oidc import OIDCDiscoveryError
from app.adapters.auth.permissions import (
    get_districts_where_user_has_role,
)
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class OIDCTokenExchangeRequest(BaseModel):
    """Parameters forwarded from frontend to OIDC provider token endpoint.

    The backend adds client_id and client_secret server-side so the secret
    is never exposed to the browser.
    """

    grant_type: str = "authorization_code"
    code: str
    redirect_uri: str
    code_verifier: str


@router.get("/oidc/discovery")
async def get_oidc_discovery() -> dict:
    """Return the OIDC discovery document.

    Proxies the provider's .well-known/openid-configuration through the backend.
    The backend caches the result for 1 hour.

    Includes additional frontend-facing config (client_id) so the frontend
    can obtain all OIDC parameters at runtime without build-time env vars.

    This endpoint is intentionally **unauthenticated** — the frontend needs
    it *before* it can initiate the OIDC login flow.
    """
    adapter = get_oidc_adapter()
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC adapter not initialized",
        )
    try:
        discovery = await adapter.discover()
        return {
            **discovery,
            # Extra frontend config — not part of the OIDC spec but needed
            # by the SPA to initiate the authorization flow.
            "client_id": adapter.client_id,
        }
    except OIDCDiscoveryError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OIDC discovery failed: {e}",
        ) from e


@router.post("/oidc/token")
async def exchange_oidc_token(body: OIDCTokenExchangeRequest) -> dict:
    """Proxy token exchange to the OIDC provider's token endpoint.

    The frontend sends the authorization code + PKCE verifier.
    The backend adds client_id and client_secret (never exposed to the browser)
    and forwards the request to the provider.

    This endpoint is intentionally **unauthenticated** — it is called during
    the OIDC callback flow when no session exists yet.
    """
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

    # Forward to the OIDC provider with server-side credentials
    client = await adapter.get_httpx_client()
    data: dict[str, str] = {
        "grant_type": body.grant_type,
        "code": body.code,
        "redirect_uri": body.redirect_uri,
        "code_verifier": body.code_verifier,
        "client_id": adapter.client_id,
        "client_secret": adapter.client_secret,
    }

    try:
        response = await client.post(token_endpoint, data=data, timeout=15)
        if not response.is_success:
            detail: dict | str = {"error": "token_exchange_failed"}
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=detail,
            )
        return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token exchange failed: {e}",
        ) from e


@router.get("/me", response_model=UserOut)
async def get_current_user_info(user: AuthenticatedUser) -> UserOut:
    """Get current authenticated user info.

    Returns the authenticated user's information extracted from the JWT token.

    **Security:** Requires valid Bearer token in Authorization header.
    """
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
    """Return effective memberships for access-aware frontend UX.
    
    **Security:** Requires valid Bearer token.
    **RBAC:** Requires VIEWER role in at least one district or superadmin.
    """
    # RBAC Guard: User must have VIEWER role in at least one district
    districts_with_viewer = get_districts_where_user_has_role(
        auth, Role.VIEWER
    )
    if not districts_with_viewer and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Benutzer mit VIEWER-Rolle in mindestens einem Bezirk können auf diese Ressource zugreifen.",
        )
    
    memberships = [
        MembershipOut(
            role=m.role.value,
            scope_type=m.scope_type.value,
            scope_id=str(m.scope_id),
        )
        for m in auth.memberships
    ]

    access_status = "ACTIVE" if auth.user.is_superadmin or memberships else "PENDING_APPROVAL"
    return AccessContextOut(status=access_status, memberships=memberships)
