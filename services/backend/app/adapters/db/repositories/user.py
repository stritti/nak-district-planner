# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""UserRepository — SQLAlchemy implementation for User persistence.

Handles CRUD operations for User entities extracted from OIDC tokens.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
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
    # Superadmin status is owner-controlled. Runtime connections must not write
    # users.is_superadmin because RLS policies trust it for global access.
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
            # Superadmin status is owner-controlled; do not update it from
            # runtime OIDC profile refreshes.
            orm.updated_at = datetime.now(UTC)

        await self._session.flush()

    async def list_all(self) -> list[User]:
        """All registered users, ordered by name for administration lists."""
        result = await self._session.execute(select(UserORM).order_by(UserORM.name, UserORM.email))
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_by_subs(self, subs: set[str]) -> list[User]:
        """The users with the given subjects, ordered like ``list_all``."""
        if not subs:
            return []
        result = await self._session.execute(
            select(UserORM).where(UserORM.sub.in_(subs)).order_by(UserORM.name, UserORM.email)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def set_superadmin(self, target_sub: str, value: bool) -> str:
        """Change the flag through the locked SECURITY DEFINER path (the only writer)."""
        result = await self._session.execute(
            text("SELECT set_user_superadmin(:target_sub, :value)"),
            {"target_sub": target_sub, "value": value},
        )
        return str(result.scalar_one())

    async def has_any_user(self) -> bool:
        result = await self._session.execute(select(UserORM.id).limit(1))
        return result.scalar_one_or_none() is not None
