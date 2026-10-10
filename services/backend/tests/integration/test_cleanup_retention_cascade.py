"""PostgreSQL regression tests for planning retention cleanup.

The unit tests assert that ``cleanup_old_events`` issues a delete against
``planning_slots``. These integration tests verify the database contract that
makes the cleanup complete: deleting a planning slot must cascade to its
``event_instances`` row, while rows on or after the retention cutoff remain.

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import delete, event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.orm_models.event_instance import EventInstanceORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.session import _set_tenant_gucs
from app.application.tasks import (
    _delete_expired_drafts,
    _run_as_system_worker,
    _unreleased_retention_statement,
)
from app.domain.models.event_instance import EventSource, EventVisibility, SyncState
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlotStatus

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_retention_delete_cascades_instances_and_keeps_cutoff_boundary(sessions) -> None:
    district_id = uuid.uuid4()
    cutoff = date(2024, 1, 1)
    slot_dates = {
        "expired": cutoff - timedelta(days=1),
        "released": cutoff - timedelta(days=2),
        "cancelled": cutoff - timedelta(days=3),
        "boundary": cutoff,
        "current": cutoff + timedelta(days=1),
    }
    slot_ids = {name: uuid.uuid4() for name in slot_dates}
    instance_ids = {name: uuid.uuid4() for name in slot_dates}
    now = datetime.now(UTC)

    async def scenario() -> None:
        try:
            async with sessions() as db:
                await db.execute(
                    text(
                        "INSERT INTO districts (id, name, created_at, updated_at) "
                        "VALUES (:id, :name, :created_at, :updated_at)"
                    ),
                    {
                        "id": district_id,
                        "name": "Retention Test District",
                        "created_at": now,
                        "updated_at": now,
                    },
                )

                for name, planning_date in slot_dates.items():
                    slot_id = slot_ids[name]
                    db.add(
                        PlanningSlotORM(
                            id=slot_id,
                            district_id=district_id,
                            congregation_id=None,
                            category="Gottesdienst",
                            title=f"Retention {name}",
                            applicability=[],
                            planning_date=planning_date,
                            planning_time=time(10, 0),
                            status=(
                                PlanningSlotStatus.CANCELLED if name == "cancelled"
                                else PlanningSlotStatus.ACTIVE
                            ),
                            approval_status=(
                                EventApprovalStatus.CONFIRMED
                                if name in ("released", "cancelled") else None
                            ),
                            released_at=(now if name in ("released", "cancelled") else None),
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    await db.flush()

                    start_at = datetime.combine(planning_date, time(10, 0), tzinfo=UTC)
                    db.add(
                        EventInstanceORM(
                            id=instance_ids[name],
                            planning_slot_id=slot_id,
                            title=f"Retention {name}",
                            actual_start_at=start_at,
                            actual_end_at=start_at + timedelta(hours=1),
                            source=EventSource.INTERNAL,
                            visibility=EventVisibility.INTERNAL,
                            deviation_flag=False,
                            sync_state=SyncState.CLEAN,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                await db.commit()

            async with sessions() as db:
                result = await db.execute(
                    _unreleased_retention_statement(cutoff)
                )
                assert result.rowcount == 1
                await db.commit()

            async with sessions() as db:
                remaining_slots = set(
                    (
                        await db.execute(
                            select(PlanningSlotORM.id).where(
                                PlanningSlotORM.id.in_(list(slot_ids.values()))
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                remaining_instances = set(
                    (
                        await db.execute(
                            select(EventInstanceORM.id).where(
                                EventInstanceORM.id.in_(list(instance_ids.values()))
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                assert slot_ids["expired"] not in remaining_slots
                assert instance_ids["expired"] not in remaining_instances
                assert slot_ids["released"] in remaining_slots
                assert instance_ids["released"] in remaining_instances
                assert slot_ids["cancelled"] in remaining_slots
                assert instance_ids["cancelled"] in remaining_instances
                assert slot_ids["boundary"] in remaining_slots
                assert instance_ids["boundary"] in remaining_instances
                assert slot_ids["current"] in remaining_slots
                assert instance_ids["current"] in remaining_instances
        finally:
            async with sessions() as db:
                await db.execute(
                    delete(PlanningSlotORM).where(PlanningSlotORM.district_id == district_id)
                )
                await db.execute(text("DELETE FROM districts WHERE id = :id"), {"id": district_id})
                await db.commit()

    await _run_as_system_worker(scenario())


async def test_retention_removes_draft_invitation_relationships_and_cancels_released_copy(sessions):
    """Retention uses aggregate deletion, preserving published invitation copies."""
    from app.adapters.db.orm_models.congregation import CongregationORM
    from app.adapters.db.orm_models.invitation import CongregationInvitationORM
    from app.domain.models.invitation import InvitationTargetType

    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    source_id = uuid.uuid4()
    draft_target_id = uuid.uuid4()
    released_target_id = uuid.uuid4()
    invitation_ids = [uuid.uuid4(), uuid.uuid4()]
    now = datetime.now(UTC)
    old_date = date(2023, 10, 1)
    cutoff = date(2024, 1, 1)

    async def scenario():
        try:
            async with sessions() as db:
                await db.execute(
                    text(
                        "INSERT INTO districts (id, name, created_at, updated_at) "
                        "VALUES (:id, :name, :created_at, :updated_at)"
                    ),
                    {
                        "id": district_id, "name": "Invitation Retention",
                        "created_at": now, "updated_at": now,
                    },
                )
                db.add(CongregationORM(
                    id=congregation_id, name="Retention Gemeinde",
                    district_id=district_id, created_at=now, updated_at=now,
                ))
                await db.flush()
                for slot_id, approved in (
                    (source_id, False), (draft_target_id, False), (released_target_id, True),
                ):
                    db.add(PlanningSlotORM(
                        id=slot_id, district_id=district_id,
                        congregation_id=None, planning_date=old_date if slot_id == source_id
                        else cutoff + timedelta(days=1),
                        planning_time=time(10),
                        category="Gottesdienst", applicability=[],
                        approval_status=EventApprovalStatus.CONFIRMED if approved else None,
                        released_at=now if approved else None,
                        status=PlanningSlotStatus.ACTIVE,
                        invitation_source_event_id=source_id if slot_id != source_id else None,
                        invitation_source_congregation_id=congregation_id
                        if slot_id != source_id else None,
                        created_at=now, updated_at=now,
                    ))
                await db.flush()
                for invitation_id, target_id in zip(
                    invitation_ids, [draft_target_id, released_target_id], strict=True
                ):
                    db.add(CongregationInvitationORM(
                        id=invitation_id, source_event_id=source_id,
                        source_planning_slot_id=source_id,
                        source_congregation_id=congregation_id,
                        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                        target_congregation_id=congregation_id,
                        linked_event_id=target_id, created_at=now, updated_at=now,
                    ))
                await db.commit()

            async with sessions() as db:
                assert await _delete_expired_drafts(db, cutoff) == 1
                await db.commit()

            async with sessions() as db:
                slots = {
                    slot.id: slot for slot in (
                        await db.execute(select(PlanningSlotORM).where(
                            PlanningSlotORM.district_id == district_id
                        ))
                    ).scalars().all()
                }
                invitations = (await db.execute(
                    select(CongregationInvitationORM).where(
                        CongregationInvitationORM.id.in_(invitation_ids)
                    )
                )).scalars().all()
                assert source_id not in slots
                assert draft_target_id not in slots
                assert released_target_id in slots
                assert slots[released_target_id].status == PlanningSlotStatus.CANCELLED
                assert slots[released_target_id].approval_status == EventApprovalStatus.CONFIRMED
                assert slots[released_target_id].invitation_source_event_id is None
                assert invitations == []
        finally:
            async with sessions() as db:
                await db.execute(delete(PlanningSlotORM).where(
                    PlanningSlotORM.district_id == district_id
                ))
                await db.execute(text("DELETE FROM districts WHERE id = :id"), {"id": district_id})
                await db.commit()

    await _run_as_system_worker(scenario())
