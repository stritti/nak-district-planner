# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/repositories/leader.py: Module."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.leader import LeaderAssignmentORM, LeaderORM
from app.domain.models.leader import Leader, LeaderAssignment, LeaderRank, SpecialRole
from app.domain.ports.repositories import LeaderRepository


def _assignment_to_domain(row: LeaderAssignmentORM) -> LeaderAssignment:
    return LeaderAssignment(
        id=row.id,
        leader_id=row.leader_id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        role=SpecialRole(row.role) if row.role else None,
        is_home=row.is_home,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _orm_to_domain(row: LeaderORM) -> Leader:
    return Leader(
        id=row.id,
        name=row.name,
        district_id=row.district_id,
        rank=LeaderRank(row.rank) if row.rank else None,
        user_sub=row.user_sub,
        email=row.email,
        phone=row.phone,
        notes=row.notes,
        is_active=row.is_active,
        hidden_from_lists=row.hidden_from_lists,
        service_end_date=row.service_end_date,
        created_at=row.created_at,
        updated_at=row.updated_at,
        assignments=[_assignment_to_domain(a) for a in row.assignments],
    )


def _sync_assignments(row: LeaderORM, assignments: list[LeaderAssignment]) -> None:
    """Make ``row.assignments`` equal to the domain list (update, add, remove by id)."""
    existing = {a.id: a for a in row.assignments}
    wanted = {a.id for a in assignments}
    for stale in [a for a in row.assignments if a.id not in wanted]:
        row.assignments.remove(stale)
    for assignment in assignments:
        orm = existing.get(assignment.id)
        if orm is None:
            orm = LeaderAssignmentORM(id=assignment.id)
            row.assignments.append(orm)
        orm.leader_id = assignment.leader_id
        orm.district_id = assignment.district_id
        orm.congregation_id = assignment.congregation_id
        orm.role = assignment.role.value if assignment.role else None
        orm.is_home = assignment.is_home
        orm.created_at = assignment.created_at
        orm.updated_at = assignment.updated_at


class SqlLeaderRepository(LeaderRepository):
    """SQLAlchemy repository for Leader."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, leader_id: uuid.UUID) -> Leader | None:
        row = await self._session.get(LeaderORM, leader_id, populate_existing=True)
        return _orm_to_domain(row) if row else None

    async def get_for_update(self, leader_id: uuid.UUID) -> Leader | None:
        """Refresh the leader row while holding a transaction-scoped write lock."""
        row = await self._session.get(
            LeaderORM, leader_id, with_for_update=True, populate_existing=True
        )
        return _orm_to_domain(row) if row else None

    async def list_by_district(
        self,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[Leader]:
        stmt = select(LeaderORM).where(LeaderORM.district_id == district_id)
        if congregation_id is not None:
            stmt = stmt.where(
                LeaderORM.assignments.any(LeaderAssignmentORM.congregation_id == congregation_id)
            )
        if active_only:
            stmt = stmt.where(LeaderORM.is_active.is_(True), LeaderORM.hidden_from_lists.is_(False))
        stmt = stmt.order_by(LeaderORM.name)
        result = await self._session.execute(stmt)
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def get_by_user_sub(
        self,
        user_sub: str,
        district_id: uuid.UUID | None = None,
    ) -> Leader | None:
        stmt = select(LeaderORM).where(LeaderORM.user_sub == user_sub)
        if district_id is not None:
            stmt = stmt.where(LeaderORM.district_id == district_id)
        result = await self._session.execute(stmt.order_by(LeaderORM.updated_at.desc()))
        row = result.scalars().first()
        return _orm_to_domain(row) if row else None

    async def save(self, leader: Leader) -> None:
        existing = await self._session.get(LeaderORM, leader.id)
        if existing is None:
            row = LeaderORM()
            self._session.add(row)
        else:
            row = existing
        row.id = leader.id
        row.name = leader.name
        row.district_id = leader.district_id
        row.rank = leader.rank.value if leader.rank else None
        row.user_sub = leader.user_sub
        row.email = leader.email
        row.phone = leader.phone
        row.notes = leader.notes
        row.is_active = leader.is_active
        row.hidden_from_lists = leader.hidden_from_lists
        row.service_end_date = leader.service_end_date
        row.created_at = leader.created_at
        row.updated_at = leader.updated_at
        if existing is None:
            # A transient row must not lazy-load its (empty) collection in async code.
            row.assignments = []
        _sync_assignments(row, leader.assignments)
        await self._session.flush()

    async def delete(self, leader_id: uuid.UUID) -> None:
        row = await self._session.get(LeaderORM, leader_id, populate_existing=True)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()
