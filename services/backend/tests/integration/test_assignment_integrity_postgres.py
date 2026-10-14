# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Assignment integrity against PostgreSQL with two concurrent sessions (#468).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.api.routers import service_assignments as sa_router
from app.adapters.api.schemas.service_assignment import ServiceAssignmentCreate
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.adapters.db.session import _set_tenant_gucs

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)

DAY = date(2031, 5, 4)
_MIGRATION = Path(__file__).parents[2] / "alembic/versions/20261007_assignment_unique.py"


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def tenant(sessions):
    """District with two congregations, two simultaneous slots and one leader; plus a foreign leader."""
    ids = {k: uuid.uuid4() for k in ("district", "other", "c1", "c2", "s1", "s2", "leader", "foreign")}
    now = datetime.now(UTC)
    async with sessions() as db:
        for district in ("district", "other"):
            await db.execute(
                text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, 'B', :n, :n)"),
                {"id": ids[district], "n": now},
            )
        for cong in ("c1", "c2"):
            await db.execute(
                text(
                    "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                    "VALUES (:id, 'G', :d, :n, :n)"
                ),
                {"id": ids[cong], "d": ids["district"], "n": now},
            )
        for slot, cong in (("s1", "c1"), ("s2", "c2")):
            # No EventInstance: the conflict check must fall back to the planned time.
            await db.execute(
                text(
                    "INSERT INTO planning_slots (id, district_id, congregation_id, category, "
                    "planning_date, planning_time, status, applicability, created_at, updated_at) "
                    "VALUES (:id, :d, :c, 'Gottesdienst', :day, '09:30', 'ACTIVE', '{}', :n, :n)"
                ),
                {"id": ids[slot], "d": ids["district"], "c": ids[cong], "day": DAY, "n": now},
            )
        for leader, district in (("leader", "district"), ("foreign", "other")):
            await db.execute(
                text("INSERT INTO leaders (id, name, district_id) VALUES (:id, 'L', :d)"),
                {"id": ids[leader], "d": ids[district]},
            )
        await db.commit()
    yield ids
    async with sessions() as db:
        await db.execute(
            text("DELETE FROM districts WHERE id IN (:a, :b)"), {"a": ids["district"], "b": ids["other"]}
        )
        await db.commit()


async def _assign(db, slot_id: uuid.UUID, body: ServiceAssignmentCreate):
    return await sa_router.create_assignment(
        slot_id,
        body,
        object(),
        db,
        SqlPlanningSlotRepository(db),
        SqlServiceAssignmentRepository(db),
    )


async def _still_blocked(task: asyncio.Task) -> bool:
    await asyncio.sleep(0.5)
    return not task.done()


@pytest.mark.asyncio
async def test_concurrent_assignments_cannot_double_book_a_leader(sessions, tenant) -> None:
    body = ServiceAssignmentCreate(leader_id=tenant["leader"])
    with patch.object(sa_router, "require_role_in_district"):
        async with sessions() as first, sessions() as second:
            await _assign(first, tenant["s1"], body)  # holds the leader lock, uncommitted
            competing = asyncio.create_task(_assign(second, tenant["s2"], body))

            assert await _still_blocked(competing), "second session must wait for the leader lock"
            await first.commit()
            with pytest.raises(HTTPException) as exc:
                await competing

    assert exc.value.status_code == 409
    assert exc.value.detail["conflicts"][0]["rule_id"] == "no_double_booking"


@pytest.mark.asyncio
async def test_concurrent_assignments_to_one_slot_keep_one(sessions, tenant) -> None:
    with patch.object(sa_router, "require_role_in_district"):
        async with sessions() as first, sessions() as second:
            await _assign(first, tenant["s1"], ServiceAssignmentCreate(leader_name="Pr. A"))
            competing = asyncio.create_task(
                _assign(second, tenant["s1"], ServiceAssignmentCreate(leader_name="Pr. B"))
            )

            assert await _still_blocked(competing), "unique index must hold the second insert"
            await first.commit()
            with pytest.raises(HTTPException) as exc:
                await competing

    assert exc.value.status_code == 409
    async with sessions() as db:
        count = await db.scalar(
            text("SELECT count(*) FROM service_assignments WHERE planning_slot_id = :s"),
            {"s": tenant["s1"]},
        )
    assert count == 1


@pytest.mark.asyncio
async def test_multi_day_service_blocks_leader_days_after_it_started(sessions, tenant) -> None:
    """Look-back is not limited to the default duration: a 52 h instance that began two
    days earlier still overlaps the target service and must block the leader.
    """
    retreat = uuid.uuid4()
    begin = datetime(DAY.year, DAY.month, DAY.day, 7, 30, tzinfo=UTC) - timedelta(days=2)
    async with sessions() as db:
        await db.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, congregation_id, category, "
                "planning_date, planning_time, status, applicability, created_at, updated_at) "
                "VALUES (:id, :d, :c, 'Jugendtage', :day, '07:30', 'ACTIVE', '{}', :n, :n)"
            ),
            {"id": retreat, "d": tenant["district"], "c": tenant["c2"], "day": begin.date(), "n": begin},
        )
        await db.execute(
            text(
                "INSERT INTO event_instances (id, planning_slot_id, title, actual_start_at, actual_end_at, "
                "source, visibility, created_at, updated_at) VALUES (gen_random_uuid(), :s, 'Jugendtage', "
                ":start, :end, 'INTERNAL', 'INTERNAL', :start, :start)"
            ),
            {"s": retreat, "start": begin, "end": begin + timedelta(hours=52)},
        )
        await db.commit()

    body = ServiceAssignmentCreate(leader_id=tenant["leader"])
    with patch.object(sa_router, "require_role_in_district"):
        async with sessions() as db:
            await _assign(db, retreat, body)
            await db.commit()
        async with sessions() as db:
            with pytest.raises(HTTPException) as exc:
                await _assign(db, tenant["s1"], body)

    assert exc.value.status_code == 409
    assert "no_double_booking" in {c["rule_id"] for c in exc.value.detail["conflicts"]}


@pytest.mark.asyncio
async def test_leader_of_other_district_is_rejected(sessions, tenant) -> None:
    with patch.object(sa_router, "require_role_in_district"):
        async with sessions() as db:
            with pytest.raises(HTTPException) as exc:
                await _assign(db, tenant["s1"], ServiceAssignmentCreate(leader_id=tenant["foreign"]))

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_migration_keeps_most_confirmed_then_newest_assignment(sessions, tenant) -> None:
    spec = importlib.util.spec_from_file_location("assignment_unique", _MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    rows = [  # (name, status, updated_at day) -> CONFIRMED wins over newer ASSIGNED/OPEN
        ("open-newest", "OPEN", 9),
        ("assigned-newer", "ASSIGNED", 8),
        ("confirmed-old", "CONFIRMED", 1),
        ("confirmed-older", "CONFIRMED", 1),
    ]
    async with sessions() as db:
        await db.execute(text(f"DROP INDEX {migration.INDEX_NAME}"))  # rolled back below
        for name, status, day in rows:
            created = datetime(2031, 1, 1, tzinfo=UTC) if name != "confirmed-older" else datetime(2030, 1, 1, tzinfo=UTC)
            await db.execute(
                text(
                    "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_name, "
                    "status, created_at, updated_at) VALUES (gen_random_uuid(), :s, :p, :name, "
                    ":status, :c, :u)"
                ),
                {
                    "s": tenant["s1"],
                    "p": None if name == "assigned-newer" else tenant["s1"],  # legacy row
                    "name": name,
                    "status": status,
                    "c": created,
                    "u": datetime(2031, 1, day, tzinfo=UTC),
                },
            )
        await db.execute(text(migration.BACKFILL_PLANNING_SLOT_SQL))
        await db.execute(text(migration.ARCHIVE_DUPLICATES_SQL))
        lock_down = migration.LOCK_DOWN_ARCHIVE_SQL.replace(":app_role", migration._quote_literal("nak_app"))
        await db.execute(text(lock_down))
        await db.execute(text(migration.DELETE_DUPLICATES_SQL))
        survivors = (await db.execute(text("SELECT leader_name FROM service_assignments"))).scalars().all()
        archived = (
            await db.execute(text(f"SELECT leader_name FROM {migration.ARCHIVE_TABLE} ORDER BY leader_name"))
        ).scalars().all()
        app_can_read = await db.scalar(
            text(f"SELECT has_table_privilege('nak_app', '{migration.ARCHIVE_TABLE}', 'SELECT')")
        )
        forced_rls = await db.scalar(
            text("SELECT relforcerowsecurity FROM pg_class WHERE relname = :t"), {"t": migration.ARCHIVE_TABLE}
        )

        # Downgrade puts the archived rows back and drops the archive.
        await db.execute(text(migration.RESTORE_DUPLICATES_SQL))
        restored = (
            await db.execute(text("SELECT leader_name FROM service_assignments ORDER BY leader_name"))
        ).scalars().all()
        archive_left = await db.scalar(text(f"SELECT to_regclass('{migration.ARCHIVE_TABLE}')"))
        await db.rollback()

    assert survivors == ["confirmed-old"]
    assert archived == ["assigned-newer", "confirmed-older", "open-newest"]
    assert app_can_read is False
    assert forced_rls is True
    assert restored == sorted(name for name, *_ in rows)
    assert archive_left is None


@pytest.mark.asyncio
async def test_migration_without_duplicates_leaves_no_archive(sessions, tenant) -> None:
    spec = importlib.util.spec_from_file_location("assignment_unique", _MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    async with sessions() as db:
        await db.execute(text(migration.ARCHIVE_DUPLICATES_SQL))
        lock_down = migration.LOCK_DOWN_ARCHIVE_SQL.replace(":app_role", migration._quote_literal("nak_app"))
        await db.execute(text(lock_down))
        archive = await db.scalar(text(f"SELECT to_regclass('{migration.ARCHIVE_TABLE}')"))
        await db.rollback()

    assert archive is None
