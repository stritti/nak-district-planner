# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQL side of the matrix conflicts with duties and absences.

The matrix loads the absences of all assigned leaders in one query and asks the duty
lookup with a placeholder slot id. TEST_DATABASE_URL must identify a migrated
disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.api.matrix_builder import _NO_SLOT
from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)

DAY = date(2031, 10, 5)
START = datetime(2031, 10, 5, 9, 0, tzinfo=UTC)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _as_app_user(db, sub: str) -> None:
    """Run as the non-owner application role with a user identity (RLS applies)."""
    await db.execute(text("SELECT set_config('app.current_user_sub', :sub, true)"), {"sub": sub})
    await db.execute(text("SET LOCAL ROLE nak_app"))


@pytest.fixture
async def world(sessions):
    ids = {key: uuid.uuid4() for key in (
        "district", "other_district", "c1", "leader", "second_leader", "unasked_leader",
        "foreign_leader", "absent", "second_absent", "later", "unasked", "foreign",
        "category", "slot", "duty",
    )}
    subs = {key: f"matrix-{key}-{uuid.uuid4().hex[:8]}" for key in ("viewer", "planner", "outsider")}
    now = datetime.now(UTC)
    async with sessions() as db, db.begin():
        for key in ("district", "other_district"):
            await db.execute(
                text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, :n, :t, :t)"),
                {"i": ids[key], "n": f"Matrix {ids[key]}", "t": now},
            )
        await db.execute(
            text("INSERT INTO congregations (id, name, district_id, created_at, updated_at) VALUES (:i, :n, :d, :t, :t)"),
            {"i": ids["c1"], "n": f"Gemeinde {ids['c1']}", "d": ids["district"], "t": now},
        )
        for key, district in (
            ("leader", "district"), ("second_leader", "district"),
            ("unasked_leader", "district"), ("foreign_leader", "other_district"),
        ):
            await db.execute(
                text("INSERT INTO leaders (id, name, district_id) VALUES (:i, :n, :d)"),
                {"i": ids[key], "n": f"Leiter {key}", "d": ids[district]},
            )
        absences = (
            ("absent", "leader", START - timedelta(hours=2), START + timedelta(hours=2)),
            ("second_absent", "second_leader", START, START + timedelta(days=1)),
            ("later", "leader", START + timedelta(days=3), START + timedelta(days=4)),
            ("unasked", "unasked_leader", START, START + timedelta(hours=1)),
            ("foreign", "foreign_leader", START, START + timedelta(hours=1)),
        )
        for key, leader, start_at, end_at in absences:
            await db.execute(
                text(
                    "INSERT INTO leader_unavailabilities (id, leader_id, start_at, end_at, reason, "
                    "created_at, updated_at) VALUES (:i, :l, :s, :e, 'URLAUB', :t, :t)"
                ),
                {"i": ids[key], "l": ids[leader], "s": start_at, "e": end_at, "t": now},
            )
        await db.execute(
            text(
                "INSERT INTO event_duty_categories (id, district_id, congregation_id, code, label, enabled, "
                "capacity, event_categories) VALUES (:i, :d, NULL, :c, 'Organist', true, 5, '{}')"
            ),
            {"i": ids["category"], "d": ids["district"], "c": f"org-{ids['category'].hex[:8]}"},
        )
        await db.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, congregation_id, category, planning_date, "
                "planning_time, status, applicability, created_at, updated_at) VALUES (:i, :d, :c, "
                "'Gottesdienst', :day, :tm, CAST('ACTIVE' AS planning_slot_status), '{}', :t, :t)"
            ),
            {"i": ids["slot"], "d": ids["district"], "c": ids["c1"], "day": DAY, "tm": time(9, 0), "t": now},
        )
        await db.execute(
            text(
                "INSERT INTO event_duty_assignments (id, planning_slot_id, duty_category_id, district_id, "
                "congregation_id, display_name, duty_label, linked_user_sub, normalized_name, leader_id) "
                "VALUES (:i, :s, :c, :d, NULL, 'Leiter leader', 'Organist', NULL, NULL, :l)"
            ),
            {"i": ids["duty"], "s": ids["slot"], "c": ids["category"], "d": ids["district"],
             "l": ids["leader"]},
        )
        memberships = (("viewer", "VIEWER", "district"), ("planner", "PLANNER", "district"),
                       ("outsider", "DISTRICT_ADMIN", "other_district"))
        for key, role, scope in memberships:
            await db.execute(
                text("INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) VALUES (:i, :s, :e, :s, false, :t, :t)"),
                {"i": uuid.uuid4(), "s": subs[key], "e": f"{subs[key]}@example.test", "t": now},
            )
            await db.execute(
                text("INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) VALUES (:i, :s, :r, 'DISTRICT', :sc, :t, :t)"),
                {"i": uuid.uuid4(), "s": subs[key], "r": role, "sc": ids[scope], "t": now},
            )
    yield ids, subs
    async with sessions() as db, db.begin():
        for key in ("district", "other_district"):
            await db.execute(text("DELETE FROM districts WHERE id = :i"), {"i": ids[key]})
        for sub in subs.values():
            await db.execute(text("DELETE FROM memberships WHERE user_sub = :s"), {"s": sub})
            await db.execute(text("DELETE FROM users WHERE sub = :s"), {"s": sub})


async def _absences(sessions, sub: str, leader_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    async with sessions() as db, db.begin():
        await _as_app_user(db, sub)
        found = await SqlLeaderUnavailabilityRepository(db).list_overlapping_for_leaders(
            leader_ids=leader_ids, start_at=START - timedelta(hours=1), end_at=START + timedelta(hours=3),
        )
    return {item.id for item in found}


async def test_absences_of_the_asked_leaders_in_the_window(sessions, world) -> None:
    ids, subs = world
    asked = [ids["leader"], ids["second_leader"], ids["foreign_leader"]]
    # The later absence lies outside the window; the unasked leader is not requested and
    # the foreign district's leader is hidden by row-level security.
    assert await _absences(sessions, subs["viewer"], asked) == {ids["absent"], ids["second_absent"]}


async def test_no_absences_for_a_member_of_another_district(sessions, world) -> None:
    ids, subs = world
    assert await _absences(sessions, subs["outsider"], [ids["leader"], ids["second_leader"]]) == set()


async def test_no_leaders_means_no_query(sessions, world) -> None:
    _, subs = world
    assert await _absences(sessions, subs["viewer"], []) == set()


async def _duties(sessions, sub: str, ids) -> list:
    async with sessions() as db, db.begin():
        await _as_app_user(db, sub)
        return await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name=None, leader_id=ids["leader"],
            window_start=START - timedelta(hours=1), window_end=START + timedelta(hours=3),
            exclude_slot_id=_NO_SLOT,
        )


async def test_duty_lookup_with_the_matrix_placeholder_finds_the_duty(sessions, world) -> None:
    ids, subs = world
    [duty] = await _duties(sessions, subs["planner"], ids)
    assert duty.slot_id == ids["slot"]


async def test_duty_lookup_returns_nothing_to_a_viewer(sessions, world) -> None:
    ids, subs = world
    assert await _duties(sessions, subs["viewer"], ids) == []
