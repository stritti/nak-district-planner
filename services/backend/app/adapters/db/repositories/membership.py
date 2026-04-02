"""
MembershipRepository — SQLAlchemy implementation for Membership persistence.

Handles CRUD operations for Membership entities (role assignments).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.membership import MembershipORM
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


def _orm_to_domain(row: MembershipORM) -> Membership:
    """Convert ORM model to domain model."""
    return Membership(
        id=row.id,
        user_sub=row.user_sub,
        role=Role(row.role),
        scope_type=ScopeType(row.scope_type),
        scope_id=row.scope_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _domain_to_orm(membership: Membership) -> MembershipORM:
    """Convert domain model to ORM model."""
    orm = MembershipORM()
    orm.id = membership.id
    orm.user_sub = membership.user_sub
    orm.role = membership.role.value
    orm.scope_type = membership.scope_type.value
    orm.scope_id = membership.scope_id
    orm.created_at = membership.created_at
    orm.updated_at = membership.updated_at
    return orm


class SqlMembershipRepository:
    """SQLAlchemy-based MembershipRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, membership_id: uuid.UUID) -> Membership | None:
        """Get membership by ID."""
        row = await self._session.get(MembershipORM, membership_id)
        return _orm_to_domain(row) if row else None

    async def get_by_user_and_scope(
        self,
        user_sub: str,
        scope_type: ScopeType,
        scope_id: uuid.UUID,
    ) -> Membership | None:
        """Get membership for a user in a specific scope."""
        result = await self._session.execute(
            select(MembershipORM).where(
                and_(
                    MembershipORM.user_sub == user_sub,
                    MembershipORM.scope_type == scope_type.value,
                    MembershipORM.scope_id == scope_id,
                )
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_all_by_user(self, user_sub: str) -> list[Membership]:
        """Get all memberships for a user."""
        result = await self._session.execute(
            select(MembershipORM).where(MembershipORM.user_sub == user_sub)
        )
        rows = result.scalars().all()
        return [_orm_to_domain(row) for row in rows]

    async def get_all_by_scope(
        self,
        scope_type: ScopeType,
        scope_id: uuid.UUID,
    ) -> list[Membership]:
        """Get all memberships for a specific scope."""
        result = await self._session.execute(
            select(MembershipORM).where(
                and_(
                    MembershipORM.scope_type == scope_type.value,
                    MembershipORM.scope_id == scope_id,
                )
            )
        )
        rows = result.scalars().all()
        return [_orm_to_domain(row) for row in rows]

    async def save(self, membership: Membership) -> None:
        """Create or update membership."""
        # Try to find existing membership
        existing = await self.get_by_user_and_scope(
            membership.user_sub,
            membership.scope_type,
            membership.scope_id,
        )

        if existing is None:
            # Create new membership
            orm = _domain_to_orm(membership)
            self._session.add(orm)
        else:
            # Update existing membership
            result = await self._session.execute(
                select(MembershipORM).where(MembershipORM.id == existing.id)
            )
            orm = result.scalar_one()
            orm.role = membership.role.value
            orm.updated_at = datetime.now(timezone.utc)

        await self._session.flush()

    async def delete(self, membership_id: uuid.UUID) -> None:
        """Delete membership by ID."""
        await self._session.execute(select(MembershipORM).where(MembershipORM.id == membership_id))
        row = await self._session.get(MembershipORM, membership_id)
        if row:
            await self._session.delete(row)
        await self._session.flush()
