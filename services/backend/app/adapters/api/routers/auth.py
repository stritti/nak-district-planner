"""
Authentication API routes.

- GET /api/v1/auth/me — Get current authenticated user info
"""

from fastapi import APIRouter

from app.adapters.api.deps import CurrentUser
from app.adapters.api.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def get_current_user_info(user: CurrentUser) -> UserOut:
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
    )
