"""Draft service generation against PostgreSQL: generator key and idempotency (#488).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.session import _set_tenant_gucs
from app.application.draft_service_generation import (
    GenerateDraftServicesUseCase,
    draft_service_generation_key,
)
from app.application.tasks import _run_as_system_worker
from app.domain.models.planning_slot import PlanningSlot

# Wednesdays 20:00 Europe/Berlin; the window holds 2030-03-06 and 2030-03-13.
WINDOW = {"from_date": date(2030, 3, 4), "to_date_exclusive": date(2030, 3, 18)}

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _generate(sessions, district_id: uuid.UUID) -> dict[str, int]:
    async with sessions() as db:
        result = await GenerateDraftServicesUseCase(
            district_repo=SqlDistrictRepository(db),
            congregation_repo=SqlCongregationRepository(db),
            slot_repo=SqlPlanningSlotRepository(db),
            instance_repo=SqlEventInstanceRepository(db),
        ).run_for_window(**WINDOW, district_ids={district_id})
        await db.commit()
        return result


async def test_moved_and_cancelled_drafts_are_not_regenerated(sessions) -> None:
    district_id, congregation_id = uuid.uuid4(), uuid.uuid4()

    async def execute(sql: str, **params):
        async with sessions() as db:
            result = await db.execute(text(sql), {"d": district_id, "c": congregation_id, **params})
            await db.commit()
            return result

    async def slots() -> list[tuple]:
        result = await execute(
            "SELECT planning_date, planning_time, status::text, generation_key, "
            "(SELECT count(*) FROM event_instances ei WHERE ei.planning_slot_id = ps.id) "
            "FROM planning_slots ps WHERE district_id = :d ORDER BY generation_key"
        )
        return [tuple(row) for row in result.all()]

    async def scenario() -> None:
        now = datetime.now(UTC)
        await execute(
            "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:d, 'Bezirk', :n, :n)",
            n=now,
        )
        await execute(
            "INSERT INTO congregations (id, name, district_id, service_times, created_at, "
            "updated_at) VALUES (:c, 'Gemeinde', :d, CAST(:st AS json), :n, :n)",
            st=json.dumps([{"weekday": 2, "time": "20:00"}]),
            n=now,
        )
        # Legacy draft from before the key existed: matched by date/time, then backfilled.
        await execute(
            "INSERT INTO planning_slots (id, district_id, congregation_id, category, "
            "planning_date, planning_time, status, applicability, created_at, updated_at) "
            "VALUES (:id, :d, :c, 'Gottesdienst', '2030-03-13', '19:00', 'ACTIVE', '{}', :n, :n)",
            id=uuid.uuid4(),
            n=now,
        )

        first = await _generate(sessions, district_id)
        assert (first["created"], first["adopted_existing"]) == (1, 1)
        key_06 = draft_service_generation_key(congregation_id, date(2030, 3, 6))
        key_13 = draft_service_generation_key(congregation_id, date(2030, 3, 13))
        assert [row[3] for row in await slots()] == [key_06, key_13]

        # Planner moves the first draft to 19:30 local and cancels the legacy one.
        await execute(
            "UPDATE planning_slots SET planning_time = '18:30' WHERE generation_key = :k", k=key_06
        )
        await execute(
            "UPDATE planning_slots SET status = 'CANCELLED' WHERE generation_key = :k", k=key_13
        )

        second = await _generate(sessions, district_id)
        assert (second["created"], second["skipped_existing"]) == (0, 2)
        assert await slots() == [
            (date(2030, 3, 6), time(18, 30), "ACTIVE", key_06, 1),
            (date(2030, 3, 13), time(19, 0), "CANCELLED", key_13, 0),
        ]

    async def cleanup() -> None:
        await execute(
            "DELETE FROM event_instances WHERE planning_slot_id IN "
            "(SELECT id FROM planning_slots WHERE district_id = :d)"
        )
        await execute("DELETE FROM planning_slots WHERE district_id = :d")
        await execute("DELETE FROM congregations WHERE district_id = :d")
        await execute("DELETE FROM districts WHERE id = :d")

    try:
        await _run_as_system_worker(scenario())
    finally:
        await _run_as_system_worker(cleanup())


async def test_duplicate_generation_key_insert_is_skipped_idempotently(sessions) -> None:
    district_id, congregation_id = uuid.uuid4(), uuid.uuid4()
    key = draft_service_generation_key(congregation_id, date(2030, 3, 6))

    def candidate(hour: int) -> PlanningSlot:
        return PlanningSlot.create(
            district_id=district_id,
            congregation_id=congregation_id,
            category="Gottesdienst",
            planning_date=date(2030, 3, 6),
            planning_time=time(hour, 0),
            generation_key=key,
        )

    async def scenario() -> None:
        now = datetime.now(UTC)
        async with sessions() as db:
            await db.execute(
                text(
                    "INSERT INTO districts (id, name, created_at, updated_at) "
                    "VALUES (:d, 'Bezirk', :n, :n)"
                ),
                {"d": district_id, "n": now},
            )
            await db.execute(
                text(
                    "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                    "VALUES (:c, 'Gemeinde', :d, :n, :n)"
                ),
                {"c": congregation_id, "d": district_id, "n": now},
            )
            await db.commit()

        async def insert(hour: int) -> bool:
            async with sessions() as db:
                inserted = await SqlPlanningSlotRepository(db).add_if_absent(candidate(hour))
                await asyncio.sleep(0.2)  # hold the transaction open across the race
                await db.commit()
                return inserted

        # Two concurrent transactions: the second blocks on the unique index,
        # then sees the violation and skips without aborting its transaction.
        assert sorted(await asyncio.gather(insert(18), insert(17))) == [False, True]

        async with sessions() as db:
            repo = SqlPlanningSlotRepository(db)
            assert await repo.add_if_absent(candidate(16)) is False
            # The session is still usable after the swallowed unique violation.
            stored = await repo.list_by_generation_keys(
                district_id=district_id, generation_keys=[key]
            )
            await db.commit()
        assert len(stored) == 1

    async def cleanup() -> None:
        async with sessions() as db:
            for sql in (
                "DELETE FROM planning_slots WHERE district_id = :d",
                "DELETE FROM congregations WHERE district_id = :d",
                "DELETE FROM districts WHERE id = :d",
            ):
                await db.execute(text(sql), {"d": district_id})
            await db.commit()

    try:
        await _run_as_system_worker(scenario())
    finally:
        await _run_as_system_worker(cleanup())
