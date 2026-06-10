"""Authentication API routes.

- GET /api/v1/auth/me — Get current authenticated user info
- GET /api/v1/auth/oidc/discovery — Get OIDC discovery document (proxied from provider)
"""

from fastapi import APIRouter, HTTPException, status

from app.adapters.api.deps import (
    AuthenticatedUser,
    RawCurrentUserWithMemberships,
    get_oidc_adapter,
)
from app.adapters.api.schemas.user import AccessContextOut, MembershipOut, UserOut
from app.adapters.auth.oidc import OIDCDiscoveryError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
    """Return effective memberships for access-aware frontend UX."""
    memberships = [
        MembershipOut(
            role=m.role.value,
            scope_type=m.scope_type.value,
            scope_id=str(m.scope_id),
        )
        for m in auth.memberships
    ]

    status = "ACTIVE" if auth.user.is_superadmin or memberships else "PENDING_APPROVAL"
    return AccessContextOut(status=status, memberships=memberships)
