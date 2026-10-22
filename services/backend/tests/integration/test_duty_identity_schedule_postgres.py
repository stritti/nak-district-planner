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


async def _as_system_worker(db) -> None:
    """The lookup authorises the caller from the request GUCs, like every application query."""
    await db.execute(text("SELECT set_config('app.is_system_worker', 'true', true)"))


async def _as_app_user(db, sub: str) -> None:
    """Run as the non-owner application role with a user identity (RLS applies)."""
    await db.execute(text("SELECT set_config('app.current_user_sub', :sub, true)"), {"sub": sub})
    await db.execute(text("SET LOCAL ROLE nak_app"))


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
        await _as_system_worker(db)
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=sub, normalized_name=None, leader_id=None,
            window_start=START - timedelta(hours=1, minutes=30), window_end=START + timedelta(minutes=90),
            exclude_slot_id=ids["here"],
        )
    # Cancelled slots, other districts, other days and the excluded slot never count.
    assert [d.slot_id for d in found] == [ids["same_day_other"]]
    assert found[0].strong is True and found[0].congregation_id == ids["c2"]


async def test_name_matches_are_weak_and_use_the_instance_times(sessions, world):
    ids, _ = world
    async with sessions() as db:
        await _as_system_worker(db)
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name="anna", leader_id=None,
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
            ids["district"], linked_user_sub=None, normalized_name=None, leader_id=None,
            window_start=START, window_end=START + timedelta(hours=1), exclude_slot_id=ids["here"],
        ) == []


# ── who may ask ────────────────────────────────────────────────────────────────


@pytest.fixture
async def members(sessions, world):
    ids, sub = world
    now = datetime.now(UTC)
    roles = {
        "planner_c1": ("PLANNER", "CONGREGATION", "c1", "district"),
        "viewer_c1": ("VIEWER", "CONGREGATION", "c1", "district"),
        "planner_district": ("PLANNER", "DISTRICT", "district", "district"),
        "planner_other": ("PLANNER", "DISTRICT", "other_district", "other_district"),
    }
    subs = {}
    async with sessions() as db, db.begin():
        for key, (role, scope_type, scope_key, _) in roles.items():
            user_sub = f"{key}-{uuid.uuid4().hex[:8]}"
            subs[key] = user_sub
            await db.execute(
                text("INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) VALUES (:i, :s, :e, :s, false, :n, :n)"),
                {"i": uuid.uuid4(), "s": user_sub, "e": f"{user_sub}@example.test", "n": now},
            )
            await db.execute(
                text("INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) VALUES (:i, :s, :r, :t, :sc, :n, :n)"),
                {"i": uuid.uuid4(), "s": user_sub, "r": role, "t": scope_type, "sc": ids[scope_key], "n": now},
            )
    yield ids, sub, subs
    async with sessions() as db, db.begin():
        for user_sub in subs.values():
            await db.execute(text("DELETE FROM memberships WHERE user_sub=:s"), {"s": user_sub})
            await db.execute(text("DELETE FROM users WHERE sub=:s"), {"s": user_sub})


async def _lookup_as(sessions, ids, sub, user_sub):
    async with sessions() as db, db.begin():
        await _as_app_user(db, user_sub)
        return await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=sub, normalized_name=None, leader_id=None,
            window_start=START - timedelta(hours=1, minutes=30), window_end=START + timedelta(minutes=90),
            exclude_slot_id=ids["here"],
        )


async def test_a_congregation_planner_sees_a_conflict_in_another_congregation(sessions, members):
    ids, sub, subs = members
    # Under RLS the planner of c1 cannot read the duty of c2 directly ...
    async with sessions() as db, db.begin():
        await _as_app_user(db, subs["planner_c1"])
        visible = (await db.execute(
            text("SELECT count(*) FROM event_duty_assignments WHERE planning_slot_id=:s"),
            {"s": ids["same_day_other"]},
        )).scalar_one()
    assert visible == 0
    # ... but the definer lookup tells them the person is booked there.
    found = await _lookup_as(sessions, ids, sub, subs["planner_c1"])
    assert [d.slot_id for d in found] == [ids["same_day_other"]]


async def test_a_district_planner_is_allowed_too(sessions, members):
    ids, sub, subs = members
    assert await _lookup_as(sessions, ids, sub, subs["planner_district"])


@pytest.mark.parametrize("who", ["viewer_c1", "planner_other"])
async def test_viewers_and_planners_of_other_districts_get_nothing(sessions, members, who):
    ids, sub, subs = members
    assert await _lookup_as(sessions, ids, sub, subs[who]) == []


async def test_an_unknown_or_missing_identity_gets_nothing(sessions, members):
    ids, sub, _ = members
    assert await _lookup_as(sessions, ids, sub, "nobody") == []
    async with sessions() as db, db.begin():
        await db.execute(text("SET LOCAL ROLE nak_app"))  # no user GUC at all
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=sub, normalized_name=None, leader_id=None,
            window_start=START - timedelta(hours=1, minutes=30), window_end=START + timedelta(minutes=90),
            exclude_slot_id=ids["here"],
        )
    assert found == []


# ── leader identity (step 2.2b) ───────────────────────────────────────────────


@pytest.fixture
async def leader_world(sessions, world):
    """The world plus a leader with a duty and a service in other congregations."""
    ids, _ = world
    now = datetime.now(UTC)
    leader_id, duty_slot, service_slot = uuid.uuid4(), ids["same_day_other"], uuid.uuid4()
    async with sessions() as db, db.begin():
        await db.execute(
            text("INSERT INTO leaders (id, name, district_id) VALUES (:i, 'Hans Müller', :d)"),
            {"i": leader_id, "d": ids["district"]},
        )
        # A leader-identified duty at "same_day_other" (09:30) ...
        await db.execute(
            text(
                "INSERT INTO event_duty_assignments (id, planning_slot_id, duty_category_id, district_id, "
                "congregation_id, display_name, duty_label, linked_user_sub, normalized_name, leader_id) "
                "VALUES (:i, :s, :c, :d, NULL, 'Ev. Hans Müller', 'Organist', NULL, NULL, :l)"
            ),
            {"i": uuid.uuid4(), "s": duty_slot, "c": ids["category"], "d": ids["district"], "l": leader_id},
        )
        # ... and a service the same leader leads in another slot at 11:00.
        await db.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, congregation_id, category, planning_date, "
                "planning_time, status, applicability, created_at, updated_at) VALUES (:i, :d, :c, 'Gottesdienst', "
                ":day, :t, 'ACTIVE', '{}', :n, :n)"
            ),
            {"i": service_slot, "d": ids["district"], "c": ids["c2"], "day": DAY, "t": time(11, 0), "n": now},
        )
        await db.execute(
            text(
                "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_id, status, created_at, updated_at) "
                "VALUES (:i, :s, :s, :l, 'ASSIGNED', :n, :n)"
            ),
            {"i": uuid.uuid4(), "s": service_slot, "l": leader_id, "n": now},
        )
    yield ids, leader_id, service_slot
    async with sessions() as db, db.begin():
        await db.execute(text("DELETE FROM service_assignments WHERE leader_id=:l"), {"l": leader_id})
        await db.execute(text("DELETE FROM event_duty_assignments WHERE leader_id=:l"), {"l": leader_id})
        await db.execute(text("DELETE FROM planning_slots WHERE id=:s"), {"s": service_slot})
        await db.execute(text("DELETE FROM leaders WHERE id=:l"), {"l": leader_id})


async def test_a_leader_matches_duties_and_service_assignments_strongly(sessions, leader_world):
    ids, leader_id, service_slot = leader_world
    async with sessions() as db:
        await _as_system_worker(db)
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name=None, leader_id=leader_id,
            window_start=START - timedelta(hours=2), window_end=START + timedelta(hours=5),
            exclude_slot_id=ids["here"],
        )
    assert {d.slot_id for d in found} == {ids["same_day_other"], service_slot}
    assert all(d.strong for d in found)


async def test_the_own_event_is_excluded_for_services_too(sessions, leader_world):
    ids, leader_id, service_slot = leader_world
    async with sessions() as db:
        await _as_system_worker(db)
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name=None, leader_id=leader_id,
            window_start=START - timedelta(hours=2), window_end=START + timedelta(hours=5),
            exclude_slot_id=service_slot,
        )
    assert {d.slot_id for d in found} == {ids["same_day_other"]}


async def test_a_typed_name_never_matches_a_leader_row(sessions, leader_world):
    ids, _, _ = leader_world
    async with sessions() as db:
        await _as_system_worker(db)
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name="ev. hans müller", leader_id=None,
            window_start=START - timedelta(hours=2), window_end=START + timedelta(hours=5),
            exclude_slot_id=ids["here"],
        )
    assert found == []


async def test_a_leader_lookup_requires_the_caller_to_be_a_planner(sessions, leader_world):
    ids, leader_id, _ = leader_world
    async with sessions() as db, db.begin():
        await _as_app_user(db, "nobody")
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name=None, leader_id=leader_id,
            window_start=START - timedelta(hours=2), window_end=START + timedelta(hours=5),
            exclude_slot_id=ids["here"],
        )
    assert found == []


async def test_the_identity_constraint_allows_exactly_one_identity(sessions, leader_world):
    from sqlalchemy.exc import IntegrityError

    ids, leader_id, _ = leader_world
    with pytest.raises(IntegrityError):
        async with sessions() as db, db.begin():
            await db.execute(
                text(
                    "INSERT INTO event_duty_assignments (id, planning_slot_id, duty_category_id, district_id, "
                    "display_name, duty_label, linked_user_sub, normalized_name, leader_id) VALUES (:i, :s, :c, :d, "
                    "'x', 'y', NULL, 'anna', :l)"
                ),
                {"i": uuid.uuid4(), "s": ids["here"], "c": ids["category"], "d": ids["district"], "l": leader_id},
            )



async def test_assigning_a_leader_to_a_service_checks_the_leaders_duties(sessions, leader_world):
    """Reverse direction (step 2.2d): the organist of 09:30 cannot lead the 09:00 service."""
    from app.adapters.api.conflict_checks import check_service_assignment_conflicts

    ids, leader_id, _ = leader_world
    async with sessions() as db:
        await _as_system_worker(db)
        conflicts = await check_service_assignment_conflicts(
            db, event_id=ids["here"], leader_id=leader_id
        )
    assert [(c.rule_id, c.severity.value) for c in conflicts][:1] == [("no_double_booking", "BLOCK")]


async def test_an_account_matches_its_linked_leader_outside_the_callers_leader_rls(
    sessions, leader_world, members
):
    """An account duty meets the service of the leader linked to it, even in c2 for a c1 planner."""
    ids, leader_id, service_slot = leader_world
    _, sub, subs = members
    async with sessions() as db, db.begin():
        await db.execute(text("UPDATE leaders SET user_sub=:s WHERE id=:l"), {"s": sub, "l": leader_id})
        # The leader is assigned to c2 only (home assignment), so a c1 planner cannot read it.
        await db.execute(
            text(
                "INSERT INTO leader_assignments (id, leader_id, district_id, congregation_id, role, is_home, "
                "created_at, updated_at) VALUES (:i, :l, :d, :c, NULL, true, now(), now())"
            ),
            {"i": uuid.uuid4(), "l": leader_id, "d": ids["district"], "c": ids["c2"]},
        )
    async with sessions() as db, db.begin():
        await _as_app_user(db, subs["planner_c1"])
        visible = (
            await db.execute(text("SELECT count(*) FROM leaders WHERE id=:l"), {"l": leader_id})
        ).scalar_one()
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=sub, normalized_name=None, leader_id=None,
            window_start=START - timedelta(hours=2), window_end=START + timedelta(hours=5),
            exclude_slot_id=ids["here"],
        )
    assert visible == 0  # the leader itself stays hidden from the c1 planner
    assert service_slot in {d.slot_id for d in found}
    assert all(d.strong for d in found)


# ── v4: exact intervals and symmetric name matching ───────────────────────────


@pytest.fixture
async def interval_world(sessions):
    """Own district: duties of one account on moved and long-running events, a typed-name duty."""
    now = datetime.now(UTC)
    ids = {k: uuid.uuid4() for k in (
        "district", "cat", "moved_in", "moved_out", "long_service", "typed", "linked_only", "target",
    )}
    sub, other_sub, leader_id = f"acct-{uuid.uuid4().hex[:8]}", f"other-{uuid.uuid4().hex[:8]}", uuid.uuid4()
    async with sessions() as db, db.begin():
        await db.execute(
            text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, 'B', :n, :n)"),
            {"i": ids["district"], "n": now},
        )
        for user_sub in (sub, other_sub):
            await db.execute(
                text("INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) VALUES (:i, :s, :e, :s, false, :n, :n)"),
                {"i": uuid.uuid4(), "s": user_sub, "e": f"{user_sub}@example.test", "n": now},
            )
        await db.execute(
            text("INSERT INTO leaders (id, name, district_id) VALUES (:i, 'Hans Müller', :d)"),
            {"i": leader_id, "d": ids["district"]},
        )
        await db.execute(
            text("INSERT INTO event_duty_categories (id, district_id, congregation_id, code, label, enabled, capacity, event_categories) VALUES (:i, :d, NULL, 'org', 'Organist', true, 9, '{}')"),
            {"i": ids["cat"], "d": ids["district"]},
        )

        async def slot(key, planned_day, planned_time, instance=None):
            await db.execute(
                text(
                    "INSERT INTO planning_slots (id, district_id, congregation_id, category, planning_date, planning_time, "
                    "status, applicability, created_at, updated_at) VALUES (:i, :d, NULL, 'Gottesdienst', :day, :t, "
                    "'ACTIVE', '{}', :n, :n)"
                ),
                {"i": ids[key], "d": ids["district"], "day": planned_day, "t": planned_time, "n": now},
            )
            if instance:
                await db.execute(
                    text(
                        "INSERT INTO event_instances (id, planning_slot_id, actual_start_at, actual_end_at, title, source, "
                        "visibility, sync_state, deviation_flag, created_at, updated_at) VALUES (:i, :s, :a, :b, 'GD', "
                        "'INTERNAL', 'INTERNAL', 'CLEAN', false, :n, :n)"
                    ),
                    {"i": uuid.uuid4(), "s": ids[key], "a": instance[0], "b": instance[1], "n": now},
                )

        async def duty(key, *, linked=None, normalized=None, leader=None, display="Name"):
            await db.execute(
                text(
                    "INSERT INTO event_duty_assignments (id, planning_slot_id, duty_category_id, district_id, "
                    "congregation_id, display_name, duty_label, linked_user_sub, normalized_name, leader_id) VALUES "
                    "(:i, :s, :c, :d, NULL, :n, 'Organist', :l, :nn, :ld)"
                ),
                {"i": uuid.uuid4(), "s": ids[key], "c": ids["cat"], "d": ids["district"], "n": display,
                 "l": linked, "nn": normalized, "ld": leader},
            )

        # Planned for the next day but moved onto the target day, 09:45-10:45.
        await slot("moved_in", DAY + timedelta(days=1), time(9, 0), (START + timedelta(minutes=45), START + timedelta(minutes=105)))
        await duty("moved_in", linked=sub)
        # Planned for the target day at 09:00 but moved three days away.
        await slot("moved_out", DAY, time(9, 0), (START + timedelta(days=3), START + timedelta(days=3, hours=2)))
        await duty("moved_out", linked=sub)
        # A long event planned the day before that is still running at 09:30.
        await slot("long_service", DAY - timedelta(days=1), time(20, 0), (START - timedelta(hours=13), START + timedelta(hours=1)))
        await duty("long_service", linked=sub)
        # Duties found by name only: a typed one, an account-linked one and a leader's.
        await slot("typed", DAY, time(9, 0))
        await duty("typed", normalized="hans müller")
        await slot("linked_only", DAY, time(9, 15))
        await duty("linked_only", linked=other_sub, display="Hans  Müller")
        await slot("target", DAY, time(9, 0))
    yield ids, sub, other_sub, leader_id
    async with sessions() as db, db.begin():
        await db.execute(text("DELETE FROM districts WHERE id=:i"), {"i": ids["district"]})
        for user_sub in (sub, other_sub):
            await db.execute(text("DELETE FROM users WHERE sub=:s"), {"s": user_sub})


async def _lookup_v4(sessions, ids, **identity):
    async with sessions() as db:
        await _as_system_worker(db)
        return await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=identity.get("sub"), normalized_name=identity.get("name"),
            leader_id=identity.get("leader"), window_start=START, window_end=START + timedelta(minutes=90),
            exclude_slot_id=ids["target"],
        )


async def test_instance_times_decide_not_the_planning_date(sessions, interval_world):
    ids, sub, _, _ = interval_world
    found = {d.slot_id for d in await _lookup_v4(sessions, ids, sub=sub)}
    assert ids["moved_in"] in found  # planned tomorrow, actually today
    assert ids["long_service"] in found  # planned yesterday, still running
    assert ids["moved_out"] not in found  # planned today, actually three days later


async def test_a_typed_name_finds_account_and_typed_duties_weakly(sessions, interval_world):
    ids, _, _, _ = interval_world
    found = await _lookup_v4(sessions, ids, name="hans müller")
    assert {d.slot_id for d in found} == {ids["typed"], ids["linked_only"]}
    assert all(not d.strong for d in found)  # a name never makes a match strong


async def test_a_typed_name_finds_a_leaders_duty_by_the_leaders_name(sessions, interval_world):
    ids, _, _, leader_id = interval_world
    async with sessions() as db, db.begin():
        await db.execute(
            text(
                "INSERT INTO event_duty_assignments (id, planning_slot_id, duty_category_id, district_id, "
                "congregation_id, display_name, duty_label, linked_user_sub, normalized_name, leader_id) VALUES "
                "(:i, :s, :c, :d, NULL, 'Ev. Hans Müller', 'Dirigent', NULL, NULL, :l)"
            ),
            {"i": uuid.uuid4(), "s": ids["target"], "c": ids["cat"], "d": ids["district"], "l": leader_id},
        )
    async with sessions() as db:
        await _as_system_worker(db)
        found = await SqlEventDutiesRepository(db).list_identity_schedule(
            ids["district"], linked_user_sub=None, normalized_name="hans müller", leader_id=None,
            window_start=START, window_end=START + timedelta(minutes=90), exclude_slot_id=uuid.uuid4(),
        )
    assert ids["target"] in {d.slot_id for d in found}
    assert all(not d.strong for d in found)


async def test_an_account_match_is_strong(sessions, interval_world):
    ids, sub, _, _ = interval_world
    found = await _lookup_v4(sessions, ids, sub=sub)
    assert found and all(d.strong for d in found)
