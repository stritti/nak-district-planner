# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/repositories/invitation.py: Module."""

from __future__ import annotations

import uuid
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.invitation import CongregationInvitationORM
from app.adapters.db.repository_base import SqlRepository
from app.domain.models.invitation import CongregationInvitation, InvitationTargetType
from app.domain.ports.repositories import InvitationRepository


def _orm_to_domain(row: CongregationInvitationORM) -> CongregationInvitation:
    return CongregationInvitation(
        id=row.id,
        source_event_id=row.source_event_id,
        source_planning_slot_id=row.source_planning_slot_id,
        source_congregation_id=row.source_congregation_id,
        target_type=InvitationTargetType(row.target_type),
        target_congregation_id=row.target_congregation_id,
        external_target_note=row.external_target_note,
        linked_event_id=row.linked_event_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlInvitationRepository(SqlRepository[CongregationInvitationORM, CongregationInvitation], InvitationRepository):
    """SQLAlchemy repository for Invitation."""

    orm_type = CongregationInvitationORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "source_event_id": "source_event_id",
        "source_planning_slot_id": "source_planning_slot_id",
        "source_congregation_id": "source_congregation_id",
        "target_type": "target_type",
        "target_congregation_id": "target_congregation_id",
        "external_target_note": "external_target_note",
        "linked_event_id": "linked_event_id",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }



    async def get(self, invitation_id: uuid.UUID) -> CongregationInvitation | None:
        row = await self._session.get(CongregationInvitationORM, invitation_id)
        return _orm_to_domain(row) if row else None

    async def list_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[CongregationInvitation]:
        result = await self._session.execute(
            select(CongregationInvitationORM).where(
                CongregationInvitationORM.source_event_id == source_event_id
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_source_events(
        self, source_event_ids: list[uuid.UUID]
    ) -> list[CongregationInvitation]:
        if not source_event_ids:
            return []
        result = await self._session.execute(
            select(CongregationInvitationORM).where(
                CongregationInvitationORM.source_event_id.in_(source_event_ids)
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]


    async def list_by_source_planning_slot(
        self, source_planning_slot_id: uuid.UUID
    ) -> list[CongregationInvitation]:
        """List invitations by source planning slot ID."""
        result = await self._session.execute(
            select(CongregationInvitationORM).where(
                CongregationInvitationORM.source_planning_slot_id == source_planning_slot_id
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_source_planning_slots(
        self, source_planning_slot_ids: list[uuid.UUID]
    ) -> list[CongregationInvitation]:
        """List invitations by multiple source planning slot IDs."""
        if not source_planning_slot_ids:
            return []
        result = await self._session.execute(
            select(CongregationInvitationORM).where(
                CongregationInvitationORM.source_planning_slot_id.in_(source_planning_slot_ids)
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def delete(self, invitation_id: uuid.UUID) -> None:
        row = await self._session.get(CongregationInvitationORM, invitation_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()
