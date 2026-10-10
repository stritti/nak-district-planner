from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.locks import acquire_advisory_xact_lock
from app.adapters.db.orm_models.deleted_generation_key import DeletedGenerationKeyORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
    ReleasedEventError,
)
from app.domain.ports.repositories import PlanningSlotRepository

_UNIQUE_VIOLATION = "23505"
# Namespaces the per-district generator lock apart from other advisory locks
# that are keyed by plain entity UUIDs.
_GENERATION_LOCK_NAMESPACE = uuid.UUID("5d0c2f4e-4b8a-4c63-9a57-2b1f0e8d4c11")


def _sqlstate(exc: IntegrityError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def _orm_to_domain(row: PlanningSlotORM) -> PlanningSlot:
    return PlanningSlot(
        id=row.id,
        series_id=row.series_id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        category=row.category,
        title=row.title,
        approval_status=row.approval_status,
        invitation_source_congregation_id=row.invitation_source_congregation_id,
        invitation_source_event_id=row.invitation_source_event_id,
        applicability=row.applicability or [],
        generation_key=row.generation_key,
        released_at=row.released_at,
        planning_date=row.planning_date,
        planning_time=row.planning_time,
        status=PlanningSlotStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlPlanningSlotRepository(PlanningSlotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, slot_id: uuid.UUID) -> PlanningSlot | None:
        row = await self._session.get(PlanningSlotORM, slot_id)
        return _orm_to_domain(row) if row else None

    async def get_by_series_and_date(
        self, series_id: uuid.UUID, planning_date: date
    ) -> PlanningSlot | None:
        """Get PlanningSlot by series_id and planning_date."""
        result = await self._session.execute(
            select(PlanningSlotORM)
            .where(
                PlanningSlotORM.series_id == series_id,
                PlanningSlotORM.planning_date == planning_date,
            )
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_series_date(
        self,
        *,
        series_id: uuid.UUID,
        planning_date: date,
        congregation_id: uuid.UUID | None,
    ) -> PlanningSlot | None:
        """Get PlanningSlot by series, date, and congregation (auto-matching)."""
        result = await self._session.execute(
            select(PlanningSlotORM).where(
                PlanningSlotORM.series_id == series_id,
                PlanningSlotORM.planning_date == planning_date,
                PlanningSlotORM.congregation_id == congregation_id,
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_for_date_range(
        self,
        *,
        district_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[PlanningSlot]:
        result = await self._session.execute(
            select(PlanningSlotORM)
            .where(
                PlanningSlotORM.district_id == district_id,
                PlanningSlotORM.planning_date >= from_date,
                PlanningSlotORM.planning_date <= to_date,
            )
            .order_by(PlanningSlotORM.planning_date, PlanningSlotORM.planning_time)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_by_generation_keys(
        self, *, district_id: uuid.UUID, generation_keys: Collection[str]
    ) -> list[PlanningSlot]:
        if not generation_keys:
            return []
        result = await self._session.execute(
            select(PlanningSlotORM).where(
                PlanningSlotORM.district_id == district_id,
                PlanningSlotORM.generation_key.in_(list(generation_keys)),
            )
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_deleted_generation_keys(
        self, *, district_id: uuid.UUID, generation_keys: Collection[str]
    ) -> set[str]:
        if not generation_keys:
            return set()
        result = await self._session.execute(
            select(DeletedGenerationKeyORM.generation_key).where(
                DeletedGenerationKeyORM.district_id == district_id,
                DeletedGenerationKeyORM.generation_key.in_(list(generation_keys)),
            )
        )
        return set(result.scalars().all())

    async def save(self, slot: PlanningSlot) -> None:
        existing = await self._session.get(PlanningSlotORM, slot.id)
        if existing is not None:
            slot.forget_generation_key_if_reassigned(
                district_id=existing.district_id,
                congregation_id=existing.congregation_id,
                category=existing.category,
            )
        if existing is not None and (existing.released_at is not None or existing.approval_status == EventApprovalStatus.CONFIRMED):
            if slot.approval_status != EventApprovalStatus.CONFIRMED:
                raise ReleasedEventError("Freigegebene Ereignisse können nicht zurückgestuft werden.")
            slot.released_at = existing.released_at or existing.updated_at
        elif slot.approval_status == EventApprovalStatus.CONFIRMED:
            slot.released_at = datetime.now(UTC)
        row = existing or PlanningSlotORM()
        self._apply(row, slot)
        if existing is None:
            self._session.add(row)
        await self._session.flush()

    async def lock_district_for_generation(self, district_id: uuid.UUID) -> None:
        await acquire_advisory_xact_lock(
            self._session, uuid.uuid5(_GENERATION_LOCK_NAMESPACE, str(district_id))
        )

    async def add_if_absent(self, slot: PlanningSlot) -> bool:
        """Insert inside a SAVEPOINT; a unique violation only rolls back the savepoint.

        A concurrent transaction inserting the same generation key blocks on the
        unique index until it commits, then this insert fails with 23505 and is
        reported as skipped. The ORM path is kept (instead of ON CONFLICT) so the
        domain audit ``after_flush`` hook still records generated slots.
        """
        row = PlanningSlotORM()
        self._apply(row, slot)
        try:
            async with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            if _sqlstate(exc) != _UNIQUE_VIOLATION:
                raise
            return False
        return True

    @staticmethod
    def _apply(row: PlanningSlotORM, slot: PlanningSlot) -> None:
        row.id = slot.id
        row.series_id = slot.series_id
        row.district_id = slot.district_id
        row.congregation_id = slot.congregation_id
        row.category = slot.category
        row.title = slot.title
        row.approval_status = slot.approval_status
        row.invitation_source_congregation_id = slot.invitation_source_congregation_id
        row.invitation_source_event_id = slot.invitation_source_event_id
        row.applicability = slot.applicability
        row.generation_key = slot.generation_key
        row.released_at = slot.released_at or (datetime.now(UTC) if slot.is_confirmed else None)
        row.planning_date = slot.planning_date
        row.planning_time = slot.planning_time
        row.status = slot.status
        row.created_at = slot.created_at
        row.updated_at = slot.updated_at

    async def delete(self, slot_id: uuid.UUID) -> None:
        # Lock before checking publication: a concurrent release must not race a deletion.
        row = (await self._session.execute(
            select(PlanningSlotORM).where(PlanningSlotORM.id == slot_id).with_for_update()
        )).scalar_one_or_none()
        if row is None:
            return
        if row.released_at is not None or row.approval_status == EventApprovalStatus.CONFIRMED:
            raise ReleasedEventError("Freigegebene Ereignisse dürfen nur abgesagt werden.")
        if row.generation_key is not None:
            # The key survives in a separate ledger: the draft itself (and its
            # dependent occurrence/assignments) is physically deleted.
            self._session.add(DeletedGenerationKeyORM(
                district_id=row.district_id,
                generation_key=row.generation_key,
                deleted_at=datetime.now(UTC),
            ))
        await self._session.delete(row)
        await self._session.flush()
