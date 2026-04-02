import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.auth.oidc import OIDCAdapter, TokenValidationError
from app.adapters.db.repositories.user import SqlUserRepository
from app.adapters.db.session import get_db_session
from app.domain.models.user import User

logger = logging.getLogger(__name__)

# OIDC Bearer token security scheme
_bearer_scheme = HTTPBearer(auto_error=False)

# Global OIDC adapter instance (initialized in main.py)
_oidc_adapter: OIDCAdapter | None = None


def set_oidc_adapter(adapter: OIDCAdapter) -> None:
    """Set the global OIDC adapter instance (called from main.py)."""
    global _oidc_adapter
    _oidc_adapter = adapter


async def get_current_user(
    credentials: HTTPAuthCredentials | None = Security(_bearer_scheme),
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
        user_info = _oidc_adapter.extract_user_info(token_claims)

        # Get or create user in database
        user_repo = SqlUserRepository(session)
        existing_user = await user_repo.get_by_sub(user_info["sub"])

        if existing_user:
            # Update existing user with latest info from token
            existing_user.email = user_info["email"]
            existing_user.username = user_info["username"]
            existing_user.name = user_info["name"]
            existing_user.given_name = user_info["given_name"]
            existing_user.family_name = user_info["family_name"]
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
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
