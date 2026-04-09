import logging
from datetime import datetime, timezone
from typing import Annotated, NamedTuple

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.auth.oidc import OIDCAdapter, TokenValidationError
from app.adapters.auth.jwt_claims import extract_memberships_from_claims
from app.adapters.db.repositories.leader_registration import SqlLeaderRegistrationRepository
from app.adapters.db.repositories.membership import SqlMembershipRepository
from app.adapters.db.repositories.user import SqlUserRepository
from app.adapters.db.session import get_db_session
from app.config import settings
from app.domain.models.membership import Membership
from app.domain.models.user import User

logger = logging.getLogger(__name__)

# OIDC Bearer token security scheme
_bearer_scheme = HTTPBearer(auto_error=False)

# Global OIDC adapter instance (initialized in main.py)
_oidc_adapter: OIDCAdapter | None = None


def set_oidc_adapter(adapter: OIDCAdapter | None) -> None:
    """Set the global OIDC adapter instance (called from main.py)."""
    global _oidc_adapter
    _oidc_adapter = adapter


def get_oidc_adapter() -> OIDCAdapter | None:
    """Get the currently configured global OIDC adapter instance."""
    return _oidc_adapter


# Context for passing token claims through dependency chain
_token_claims_context: dict = {}


def set_token_claims(claims: dict) -> None:
    """Store token claims in context for use in dependent functions."""
    _token_claims_context.update(claims)


def get_token_claims() -> dict:
    """Get current token claims from context."""
    return _token_claims_context.copy()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependency to extract and validate current user from Bearer token.

    - Validates JWT signature, issuer, expiration
    - Auto-creates user on first login
    - Returns authenticated User object

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if _oidc_adapter is None:
        logger.error("OIDC adapter not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not available",
        )

    try:
        # Validate token and extract claims
        token_claims = await _oidc_adapter.validate_token(token)
        # Store claims in context for dependent functions
        set_token_claims(token_claims)

        user_info = _oidc_adapter.extract_user_info(token_claims)

        # Get or create user in database
        user_repo = SqlUserRepository(session)
        existing_user = await user_repo.get_by_sub(user_info["sub"])
        if settings.superadmin_sub is not None:
            is_superadmin = user_info["sub"] == settings.superadmin_sub
        else:
            has_any_user = await user_repo.has_any_user()
            is_superadmin = existing_user.is_superadmin if existing_user else (not has_any_user)

        if existing_user:
            # Update existing user with latest info from token
            existing_user.email = user_info["email"]
            existing_user.username = user_info["username"]
            existing_user.name = user_info["name"]
            existing_user.given_name = user_info["given_name"]
            existing_user.family_name = user_info["family_name"]
            existing_user.is_superadmin = is_superadmin
            await user_repo.save(existing_user)
            return existing_user
        else:
            # Auto-create user on first login
            new_user = User(
                sub=user_info["sub"],
                email=user_info["email"],
                username=user_info["username"],
                name=user_info["name"],
                given_name=user_info["given_name"],
                family_name=user_info["family_name"],
                is_superadmin=is_superadmin,
            )
            await user_repo.save(new_user)
            logger.info(f"Auto-created user: {new_user.sub} ({new_user.email})")
            return new_user

    except TokenValidationError as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e


class CurrentUserContext(NamedTuple):
    """User context with RBAC information."""

    user: User
    memberships: list[Membership]

    # Properties for easy access in authorization checks
    @property
    def user_sub(self) -> str:
        return self.user.sub


async def get_current_user_with_memberships(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserContext:
    """
    Dependency to get current user with their role memberships.

    Used for endpoints that require role-based authorization.

    Memberships are loaded from:
    1. JWT claims (if OIDC provider includes custom membership claim)
    2. Database lookup (fallback)
    """
    # Try to extract memberships from JWT claims first
    token_claims = get_token_claims()
    memberships = extract_memberships_from_claims(token_claims)

    # If no memberships in JWT claims, fetch from database
    membership_repo = SqlMembershipRepository(session)
    if not memberships:
        memberships = await membership_repo.get_all_by_user(user.sub)

    # Secure post-login linking strategy for approved registrations without user_sub:
    # if there is exactly one approved+unlinked registration for this email,
    # link it to this user and materialize its assigned membership.
    if user.email:
        reg_repo = SqlLeaderRegistrationRepository(session)
        candidates = await reg_repo.list_approved_unlinked_by_email(user.email)
        if len(candidates) == 1:
            registration = candidates[0]
            registration.user_sub = user.sub
            registration.updated_at = datetime.now(timezone.utc)
            await reg_repo.save(registration)
            if (
                registration.assigned_role is not None
                and registration.assigned_scope_type is not None
                and registration.assigned_scope_id is not None
            ):
                await membership_repo.upsert_by_scope(
                    user_sub=user.sub,
                    role=registration.assigned_role,
                    scope_type=registration.assigned_scope_type,
                    scope_id=registration.assigned_scope_id,
                )
            memberships = await membership_repo.get_all_by_user(user.sub)
        elif len(candidates) > 1:
            logger.warning(
                "Multiple approved unlinked registrations for email=%s; skipping auto-link",
                user.email,
            )

    return CurrentUserContext(user=user, memberships=memberships)


async def require_membership_access(
    auth: CurrentUserContext = Depends(get_current_user_with_memberships),
) -> CurrentUserContext:
    """Require authenticated users to have effective memberships (except superadmin)."""
    if auth.user.is_superadmin:
        return auth
    if not auth.memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Freigabe ausstehend: kein Zugriff ohne zugewiesene Berechtigung.",
        )
    return auth


async def get_current_active_user(
    auth: CurrentUserContext = Depends(require_membership_access),
) -> User:
    """Return authenticated and approved user entity."""
    return auth.user


# Type aliases for dependency injection
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
RawCurrentUserWithMemberships = Annotated[
    CurrentUserContext, Depends(get_current_user_with_memberships)
]
CurrentUserWithMemberships = Annotated[CurrentUserContext, Depends(require_membership_access)]
CurrentActiveUser = Annotated[CurrentUserContext, Depends(require_membership_access)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
