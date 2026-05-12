"""UserRepository — SQLAlchemy implementation for User persistence.

Handles CRUD operations for User entities extracted from OIDC tokens.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.user import UserORM
from app.domain.models.user import User
from app.domain.ports.repositories import UserRepository


def _orm_to_domain(row: UserORM) -> User:
    """Convert ORM model to domain model."""
    return User(
        sub=row.sub,
        email=row.email,
        username=row.username,
        name=row.name,
        given_name=row.given_name,
        family_name=row.family_name,
        is_superadmin=row.is_superadmin,
        created_at=row.created_at,
    )


def _domain_to_orm(user: User) -> UserORM:
    """Convert domain model to ORM model."""
    orm = UserORM()
    orm.sub = user.sub
    orm.email = user.email
    orm.username = user.username
    orm.name = user.name
    orm.given_name = user.given_name
    orm.family_name = user.family_name
    orm.is_superadmin = user.is_superadmin
    orm.created_at = user.created_at or datetime.now(UTC)
    orm.updated_at = datetime.now(UTC)
    return orm


class SqlUserRepository(UserRepository):
    """SQLAlchemy-based UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_sub(self, sub: str) -> User | None:
        """Get user by OIDC subject (user ID from IDP)."""
        result = await self._session.execute(select(UserORM).where(UserORM.sub == sub))
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self._session.execute(select(UserORM).where(UserORM.email == email))
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by internal UUID."""
        row = await self._session.get(UserORM, user_id)
        return _orm_to_domain(row) if row else None

    async def save(self, user: User) -> None:
        """Create or update user."""
        # Try to find existing user by sub
        existing = await self.get_by_sub(user.sub)

        if existing is None:
            # Create new user
            orm = _domain_to_orm(user)
            self._session.add(orm)
        else:
            # Update existing user
            result = await self._session.execute(select(UserORM).where(UserORM.sub == user.sub))
            orm = result.scalar_one()
            orm.email = user.email
            orm.username = user.username
            orm.name = user.name
            orm.given_name = user.given_name
            orm.family_name = user.family_name
            orm.is_superadmin = user.is_superadmin
            orm.updated_at = datetime.now(UTC)

        await self._session.flush()

    async def has_any_user(self) -> bool:
        result = await self._session.execute(select(UserORM.id).limit(1))
        return result.scalar_one_or_none() is not None
