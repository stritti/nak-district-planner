# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/repositories/invitation_overwrite_request.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.invitation import CongregationInvitationORM
from app.adapters.db.orm_models.invitation_overwrite_request import InvitationOverwriteRequestORM
from app.adapters.db.repository_base import SqlRepository
from app.domain.models.invitation import InvitationOverwriteRequest, OverwriteDecisionStatus
from app.domain.ports.repositories import InvitationOverwriteRequestRepository


def _orm_to_domain(row: InvitationOverwriteRequestORM) -> InvitationOverwriteRequest:
    return InvitationOverwriteRequest(
        id=row.id,
        invitation_id=row.invitation_id,
        source_event_id=row.source_event_id,
        target_event_id=row.target_event_id,
        proposed_title=row.proposed_title,
        proposed_start_at=row.proposed_start_at,
        proposed_end_at=row.proposed_end_at,
        proposed_description=row.proposed_description,
        proposed_category=row.proposed_category,
        status=OverwriteDecisionStatus(row.status),
        decided_at=row.decided_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlInvitationOverwriteRequestRepository(SqlRepository[InvitationOverwriteRequestORM, InvitationOverwriteRequest], InvitationOverwriteRequestRepository):
    """SQLAlchemy repository for InvitationOverwriteRequest."""

    orm_type = InvitationOverwriteRequestORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "invitation_id": "invitation_id",
        "source_event_id": "source_event_id",
        "target_event_id": "target_event_id",
        "proposed_title": "proposed_title",
        "proposed_start_at": "proposed_start_at",
        "proposed_end_at": "proposed_end_at",
        "proposed_description": "proposed_description",
        "proposed_category": "proposed_category",
        "status": "status",
        "decided_at": "decided_at",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }



    async def get(self, request_id: uuid.UUID) -> InvitationOverwriteRequest | None:
        row = await self._session.get(InvitationOverwriteRequestORM, request_id)
        return _orm_to_domain(row) if row else None

    async def list_open_by_district(
        self, district_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]:
        # Join through congregation_invitations → congregations to scope by district
        result = await self._session.execute(
            select(InvitationOverwriteRequestORM)
            .join(
                CongregationInvitationORM,
                CongregationInvitationORM.id == InvitationOverwriteRequestORM.invitation_id,
            )
            .join(
                CongregationORM,
                CongregationORM.id == CongregationInvitationORM.source_congregation_id,
            )
            .where(
                CongregationORM.district_id == district_id,
                InvitationOverwriteRequestORM.status == OverwriteDecisionStatus.PENDING_OVERWRITE,
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_open_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]:
        result = await self._session.execute(
            select(InvitationOverwriteRequestORM).where(
                InvitationOverwriteRequestORM.source_event_id == source_event_id,
                InvitationOverwriteRequestORM.status == OverwriteDecisionStatus.PENDING_OVERWRITE,
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]


    async def set_status(
        self,
        request_id: uuid.UUID,
        status: OverwriteDecisionStatus,
    ) -> InvitationOverwriteRequest | None:
        row = await self._session.get(InvitationOverwriteRequestORM, request_id)
        if row is None:
            return None
        row.status = status
        row.updated_at = datetime.now(UTC)
        if status != OverwriteDecisionStatus.PENDING_OVERWRITE:
            row.decided_at = row.updated_at
        await self._session.flush()
        return _orm_to_domain(row)
