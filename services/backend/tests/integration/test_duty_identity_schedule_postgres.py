# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQL side of the duty identity conflict check (step 2.2a).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)

DAY = date(2031, 9, 7)
START = datetime(2031, 9, 7, 9, 0, tzinfo=UTC)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def world(sessions):
    ids = {k: uuid.uuid4() for k in (
        "district", "other_district", "c1", "c2", "category", "other_category",
        "here", "same_day_other", "cancelled", "next_day", "foreign", "with_instance",
    )}
    sub = f"organist-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    async with sessions() as db, db.begin():
        for key in ("district", "other_district"):
            await db.execute(
                text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, 'B', :n, :n)"),
                {"i": ids[key], "n": now},
            )
        for key in ("c1", "c2"):
            await db.execute(
                text("INSERT INTO congregations (id, name, district_id, created_at, updated_at) VALUES (:i, 'G', :d, :n, :n)"),
                {"i": ids[key], "d": ids["district"], "n": now},
            )
        await db.execute(
            text("INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) VALUES (:i, :s, :e, :s, false, :n, :n)"),
            {"i": uuid.uuid4(), "s": sub, "e": f"{sub}@example.test", "n": now},
        )
        for key, district in (("category", "district"), ("other_category", "other_district")):
            await db.execute(
                text(
                    "INSERT INTO event_duty_categories (id, district_id, congregation_id, code, label, enabled, "
                    "capacity, event_categories) VALUES (:i, :d, NULL, :c, 'Organist', true, 5, '{}')"
                ),
                {"i": ids[key], "d": ids[district], "c": f"org-{key}"},
            )
        slots = [
            ("here", "c1", "district", DAY, time(9, 0), "ACTIVE"),
            ("same_day_other", "c2", "district", DAY, time(9, 30), "ACTIVE"),
            ("cancelled", "c2", "district", DAY, time(9, 15), "CANCELLED"),
            ("next_day", "c2", "district", DAY + timedelta(days=1), time(9, 0), "ACTIVE"),
            ("foreign", None, "other_district", DAY, time(9, 0), "ACTIVE"),
            ("with_instance", "c2", "district", DAY, time(14, 0), "ACTIVE"),
        ]
        for key, cong, district, day, time_, status in slots:
            await db.execute(
                text(
                    "INSERT INTO planning_slots (id, district_id, congregation_id, category, planning_date, "
                    "planning_time, status, applicability, created_at, updated_at) VALUES (:i, :d, :c, 'Gottesdienst', "
                    ":day, :t, CAST(:st AS planning_slot_status), '{}', :n, :n)"
                ),
                {"i": ids[key], "d": ids[district], "c": ids[cong] if cong else None, "day": day, "t": time_, "st": status, "n": now},
            )
        await db.execute(
            text(
                "INSERT INTO event_instances (id, planning_slot_id, actual_start_at, actual_end_at, title, source, "
                "visibility, sync_state, deviation_flag, created_at, updated_at) VALUES (:i, :s, :a, :b, 'GD', "
                "'INTERNAL', 'INTERNAL', 'CLEAN', false, :n, :n)"
            ),
            {"i": uuid.uuid4(), "s": ids["with_instance"], "a": START.replace(hour=9, minute=0) + timedelta(hours=5),
             "b": START.replace(hour=9, minute=0) + timedelta(hours=7), "n": now},
        )
        rows = [
            ("here", "district", "category", sub, None),
            ("same_day_other", "district", "category", sub, None),
            ("cancelled", "district", "category", sub, None),
            ("next_day", "district", "category", sub, None),
            ("foreign", "other_district", "other_category", sub, None),
            ("with_instance", "district", "category", None, "anna"),
        ]
        for key, district, category, linked, normalized in rows:
            await db.execute(
                text(
                    "INSERT INTO event_duty_assignments (id, planning_slot_id, duty_category_id, district_id, "
                    "congregation_id, display_name, duty_label, linked_user_sub, normalized_name) VALUES (:i, :s, :c, :d, "
                    ":g, 'Name', 'Organist', :l, :n)"
                ),
                {"i": uuid.uuid4(), "s": ids[key], "c": ids[category], "d": ids[district], "g": None,
                 "l": linked, "n": normalized},
            )
    yield ids, sub
    async with sessions() as db, db.begin():
        for key in ("district", "other_district"):
            await db.execute(text("DELETE FROM districts WHERE id = :i"), {"i": ids[key]})
        await db.execute(text("DELETE FROM users WHERE sub = :s"), {"s": sub})


async def test_finds_only_overlap_candidates_of_the_same_person_in_the_same_district(sessions, world):
    ids, sub = world
    async with sessions() as db:
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=sub, normalized_name=None,
            window_start=START - timedelta(hours=1, minutes=30), window_end=START + timedelta(minutes=90),
            exclude_slot_id=ids["here"],
        )
    # Cancelled slots, other districts, other days and the excluded slot never count.
    assert [d.slot_id for d in found] == [ids["same_day_other"]]
    assert found[0].strong is True and found[0].congregation_id == ids["c2"]


async def test_name_matches_are_weak_and_use_the_instance_times(sessions, world):
    ids, _ = world
    async with sessions() as db:
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name="anna",
            window_start=START + timedelta(hours=4), window_end=START + timedelta(hours=8),
            exclude_slot_id=ids["here"],
        )
    [duty] = found
    assert duty.slot_id == ids["with_instance"] and duty.strong is False
    assert (duty.end_time - duty.start_time) == timedelta(hours=2)  # instance, not the default


async def test_slot_schedule_reads_planned_time_or_instance(sessions, world):
    ids, _ = world
    repo_for = lambda db: SqlEventDutiesRepository(db)  # noqa: E731
    async with sessions() as db:
        planned = await repo_for(db).slot_schedule(ids["here"])
        with_instance = await repo_for(db).slot_schedule(ids["with_instance"])
        missing = await repo_for(db).slot_schedule(uuid.uuid4())
    assert planned.actual_start_at is None and planned.congregation_id == ids["c1"]
    assert with_instance.actual_start_at is not None
    assert missing is None


async def test_without_any_identity_nothing_is_returned(sessions, world):
    ids, _ = world
    async with sessions() as db:
        assert await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name=None,
            window_start=START, window_end=START + timedelta(hours=1), exclude_slot_id=ids["here"],
        ) == []
