"""SQL implementation of the slot gap ledger."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.adapters.db.orm_models.slot_gap_alert import SlotGapAlertORM
from app.domain.models.planning_slot import PlanningSlotStatus
from app.domain.ports.slot_gaps import SlotGapLedger
from app.domain.slot_gaps import GapKey, SlotGap

SERVICE_CATEGORY = "Gottesdienst"
DISTRICT_WIDE = "Bezirk"


class SqlSlotGapLedger(SlotGapLedger):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def open_gaps(self, from_date: date, to_date: date) -> Sequence[SlotGap]:
        # Same rule as the matrix: a service slot is a gap without assignment;
        # invitation copies show the source congregation's assignment.
        assigned = exists().where(
            or_(
                ServiceAssignmentORM.planning_slot_id == PlanningSlotORM.id,
                ServiceAssignmentORM.event_id == PlanningSlotORM.id,
            )
        )
        rows = await self._session.execute(
            select(
                PlanningSlotORM.id,
                PlanningSlotORM.district_id,
                PlanningSlotORM.congregation_id,
                PlanningSlotORM.planning_date,
                PlanningSlotORM.title,
                CongregationORM.name,
            )
            .outerjoin(CongregationORM, CongregationORM.id == PlanningSlotORM.congregation_id)
            .where(
                PlanningSlotORM.category == SERVICE_CATEGORY,
                PlanningSlotORM.status == PlanningSlotStatus.ACTIVE,
                PlanningSlotORM.invitation_source_event_id.is_(None),
                PlanningSlotORM.planning_date.between(from_date, to_date),
                ~assigned,
            )
        )
        return [
            SlotGap(
                key=GapKey(row.district_id, row.planning_date, row.congregation_id, row.id),
                event_title=row.title or SERVICE_CATEGORY,
                congregation_name=row.name or DISTRICT_WIDE,
            )
            for row in rows
        ]

    async def reported(self) -> Sequence[GapKey]:
        rows = await self._session.execute(select(SlotGapAlertORM))
        return [
            GapKey(a.district_id, a.service_date, a.congregation_id, a.planning_slot_id)
            for a in rows.scalars()
        ]

    async def mark_reported(self, gaps: Sequence[SlotGap]) -> None:
        if not gaps:
            return
        now = datetime.now(UTC)
        statement = insert(SlotGapAlertORM).values(
            [
                {
                    "planning_slot_id": gap.key.planning_slot_id,
                    "district_id": gap.key.district_id,
                    "congregation_id": gap.key.congregation_id,
                    "service_date": gap.key.service_date,
                    "reported_at": now,
                }
                for gap in gaps
            ]
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[SlotGapAlertORM.planning_slot_id],
                set_={
                    "district_id": statement.excluded.district_id,
                    "congregation_id": statement.excluded.congregation_id,
                    "service_date": statement.excluded.service_date,
                    "reported_at": statement.excluded.reported_at,
                },
            )
        )

    async def forget(self, keys: Sequence[GapKey]) -> None:
        if not keys:
            return
        await self._session.execute(
            delete(SlotGapAlertORM).where(
                SlotGapAlertORM.planning_slot_id.in_([key.planning_slot_id for key in keys])
            )
        )
