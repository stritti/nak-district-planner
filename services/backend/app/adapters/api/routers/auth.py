"""
Authentication API routes.

- GET /api/v1/auth/me — Get current authenticated user info
"""

from fastapi import APIRouter

from app.adapters.api.deps import AuthenticatedUser, RawCurrentUserWithMemberships
from app.adapters.api.schemas.user import AccessContextOut, MembershipOut, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def get_current_user_info(user: AuthenticatedUser) -> UserOut:
    """
    Get current authenticated user info.

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
