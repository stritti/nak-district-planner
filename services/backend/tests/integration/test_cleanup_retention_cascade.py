# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

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
from app.application.tasks import _run_as_system_worker
from app.domain.models.event_instance import EventSource, EventVisibility, SyncState
from app.domain.models.planning_slot import PlanningSlotStatus

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
                            status=PlanningSlotStatus.ACTIVE,
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
                    delete(PlanningSlotORM).where(PlanningSlotORM.planning_date < cutoff)
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
