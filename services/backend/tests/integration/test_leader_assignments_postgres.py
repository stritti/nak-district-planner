# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Leader assignments against PostgreSQL: repository, row-level security (step 4).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database whose
application role ``nak_app`` exists (created by the migrations).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.domain.models.leader import Leader, LeaderAssignment, SpecialRole

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _system(db) -> None:
    await db.execute(text("SELECT set_config('app.is_system_worker', 'true', true)"))


async def _as(db, sub: str) -> None:
    """Run as the non-owner application role with this identity (RLS applies)."""
    await db.execute(text("SELECT set_config('app.current_user_sub', :s, true)"), {"s": sub})
    await db.execute(text("SET LOCAL ROLE nak_app"))


@pytest.fixture
async def world(sessions):
    """District with congregations A, B, C; leaders L (A+B), M (C), N (district level)."""
    now = datetime.now(UTC)
    ids = {k: uuid.uuid4() for k in ("district", "other", "a", "b", "c", "x", "l", "m", "n")}
    people = {
        key: f"{key}-{uuid.uuid4().hex[:8]}"
        for key in ("planner_a", "viewer_b", "planner_c", "planner_district", "planner_other", "planner_x")
    }
    memberships = {
        "planner_a": ("PLANNER", "CONGREGATION", "a"),
        "viewer_b": ("VIEWER", "CONGREGATION", "b"),
        "planner_c": ("PLANNER", "CONGREGATION", "c"),
        "planner_district": ("PLANNER", "DISTRICT", "district"),
        "planner_other": ("PLANNER", "DISTRICT", "other"),
        "planner_x": ("PLANNER", "CONGREGATION", "x"),  # congregation of the other district
    }
    async with sessions() as db, db.begin():
        for key in ("district", "other"):
            await db.execute(
                text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, :n, :t, :t)"),
                {"i": ids[key], "n": f"D-{key}-{uuid.uuid4().hex[:6]}", "t": now},
            )
        for key in ("a", "b", "c"):
            await db.execute(
                text("INSERT INTO congregations (id, name, district_id, created_at, updated_at) VALUES (:i, :n, :d, :t, :t)"),
                {"i": ids[key], "n": f"G{key}", "d": ids["district"], "t": now},
            )
        await db.execute(
            text("INSERT INTO congregations (id, name, district_id, created_at, updated_at) VALUES (:i, 'Gx', :d, :t, :t)"),
            {"i": ids["x"], "d": ids["other"], "t": now},
        )
        for key, sub in people.items():
            await db.execute(
                text("INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) VALUES (:i, :s, :e, :s, false, :t, :t)"),
                {"i": uuid.uuid4(), "s": sub, "e": f"{sub}@example.test", "t": now},
            )
            role, scope, target = memberships[key]
            await db.execute(
                text("INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) VALUES (:i, :s, :r, :st, :sc, :t, :t)"),
                {"i": uuid.uuid4(), "s": sub, "r": role, "st": scope, "sc": ids[target], "t": now},
            )
        repo = SqlLeaderRepository(db)
        await _system(db)
        for key, name, congregations in (
            ("l", "Leiter Ein", ("a", "b")), ("m", "Leiter Zwei", ("c",)), ("n", "Bezirksleiter", (None,)),
        ):
            leader = Leader.create(name=name, district_id=ids["district"])
            leader.id = ids[key]
            leader.assignments.clear()
            for index, congregation in enumerate(congregations):
                leader.assignments.append(
                    LeaderAssignment.create(
                        leader.id, ids["district"], ids[congregation] if congregation else None,
                        SpecialRole.GEMEINDEVORSTEHER if congregation == "a" else None, is_home=index == 0,
                    )
                )
            await repo.save(leader)
    yield ids, people
    async with sessions() as db, db.begin():
        for key in ("district", "other"):
            await db.execute(text("DELETE FROM districts WHERE id=:i"), {"i": ids[key]})
        for sub in people.values():
            await db.execute(text("DELETE FROM memberships WHERE user_sub=:s"), {"s": sub})
            await db.execute(text("DELETE FROM users WHERE sub=:s"), {"s": sub})


async def _visible(sessions, sub: str, table: str, column: str, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    async with sessions() as db, db.begin():
        await _as(db, sub)
        rows = await db.execute(
            text(f"SELECT {column} FROM {table} WHERE {column} = ANY(:ids)"), {"ids": ids}  # noqa: S608
        )
        return {row[0] for row in rows}


# ── repository ───────────────────────────────────────────────────────────────


async def test_assignments_round_trip_through_the_repository(sessions, world):
    ids, _ = world
    async with sessions() as db, db.begin():
        await _system(db)
        leader = await SqlLeaderRepository(db).get(ids["l"])
    assert [(a.congregation_id, a.is_home) for a in leader.assignments] == [
        (ids["a"], True), (ids["b"], False),
    ]
    assert leader.assignments[0].role == SpecialRole.GEMEINDEVORSTEHER
    assert leader.congregation_id == ids["a"]  # transitional accessor: the home congregation


async def test_saving_updates_adds_and_removes_assignments(sessions, world):
    ids, _ = world
    async with sessions() as db, db.begin():
        await _system(db)
        repo = SqlLeaderRepository(db)
        leader = await repo.get(ids["l"])
        leader.assignments[1].role = SpecialRole.GEMEINDEVORSTEHER  # update
        leader.assignments.append(  # add
            LeaderAssignment.create(leader.id, ids["district"], ids["c"])
        )
        await repo.save(leader)
    async with sessions() as db, db.begin():
        await _system(db)
        repo = SqlLeaderRepository(db)
        reloaded = await repo.get(ids["l"])
        assert {(a.congregation_id, a.role) for a in reloaded.assignments} == {
            (ids["a"], SpecialRole.GEMEINDEVORSTEHER),
            (ids["b"], SpecialRole.GEMEINDEVORSTEHER),
            (ids["c"], None),
        }
        reloaded.assignments[:] = [a for a in reloaded.assignments if a.congregation_id != ids["b"]]  # remove
        await repo.save(reloaded)
    async with sessions() as db, db.begin():
        await _system(db)
        final = await SqlLeaderRepository(db).get(ids["l"])
    assert {a.congregation_id for a in final.assignments} == {ids["a"], ids["c"]}


async def test_listing_by_congregation_matches_any_assignment(sessions, world):
    ids, _ = world
    async with sessions() as db, db.begin():
        await _system(db)
        repo = SqlLeaderRepository(db)
        in_b = await repo.list_by_district(ids["district"], congregation_id=ids["b"])
        in_a = await repo.list_by_district(ids["district"], congregation_id=ids["a"])
        everyone = await repo.list_by_district(ids["district"])
    assert {leader.id for leader in in_b} == {ids["l"]}
    assert {leader.id for leader in in_a} == {ids["l"]}
    assert {leader.id for leader in everyone} == {ids["l"], ids["m"], ids["n"]}


async def test_the_database_allows_one_home_and_one_assignment_per_congregation(sessions, world):
    ids, _ = world
    now = datetime.now(UTC)
    insert = text(
        "INSERT INTO leader_assignments (id, leader_id, district_id, congregation_id, role, is_home, created_at, updated_at) "
        "VALUES (:i, :l, :d, :c, NULL, :h, :t, :t)"
    )
    with pytest.raises(DBAPIError):  # a second home
        async with sessions() as db, db.begin():
            await db.execute(insert, {"i": uuid.uuid4(), "l": ids["l"], "d": ids["district"], "c": ids["c"], "h": True, "t": now})
    with pytest.raises(DBAPIError):  # the same congregation twice
        async with sessions() as db, db.begin():
            await db.execute(insert, {"i": uuid.uuid4(), "l": ids["l"], "d": ids["district"], "c": ids["a"], "h": False, "t": now})
    with pytest.raises(DBAPIError):  # a second district-level row (NULLs are not distinct)
        async with sessions() as db, db.begin():
            await db.execute(insert, {"i": uuid.uuid4(), "l": ids["n"], "d": ids["district"], "c": None, "h": False, "t": now})
    with pytest.raises(DBAPIError):  # district id must match the leader's district
        async with sessions() as db, db.begin():
            await db.execute(insert, {"i": uuid.uuid4(), "l": ids["m"], "d": ids["other"], "c": ids["b"], "h": False, "t": now})


# ── row-level security ───────────────────────────────────────────────────────


async def test_a_leader_is_visible_to_every_assigned_congregation_only(sessions, world):
    ids, people = world
    everyone = [ids["l"], ids["m"], ids["n"]]
    seen = {
        who: await _visible(sessions, people[who], "leaders", "id", everyone)
        for who in ("planner_a", "viewer_b", "planner_c", "planner_district", "planner_other")
    }
    assert seen["planner_a"] == {ids["l"]}
    assert seen["viewer_b"] == {ids["l"]}  # assigned to B as well
    assert seen["planner_c"] == {ids["m"]}
    assert seen["planner_district"] == set(everyone)  # incl. the district-level leader
    assert seen["planner_other"] == set()


async def test_assignment_rows_follow_the_congregation_of_the_row(sessions, world):
    ids, people = world
    async with sessions() as db, db.begin():
        await _system(db)
        rows = await db.execute(
            text("SELECT id, congregation_id FROM leader_assignments WHERE leader_id = :l"), {"l": ids["l"]}
        )
        by_congregation = {row[1]: row[0] for row in rows}
    wanted = list(by_congregation.values())
    assert await _visible(sessions, people["planner_a"], "leader_assignments", "id", wanted) == {by_congregation[ids["a"]]}
    assert await _visible(sessions, people["viewer_b"], "leader_assignments", "id", wanted) == {by_congregation[ids["b"]]}
    assert await _visible(sessions, people["planner_district"], "leader_assignments", "id", wanted) == set(wanted)


async def _write(sessions, sub: str, statement: str, params: dict) -> int:
    async with sessions() as db, db.begin():
        await _as(db, sub)
        return (await db.execute(text(statement), params)).rowcount


async def test_a_congregation_planner_changes_only_the_assignment_of_their_congregation(sessions, world):
    ids, people = world
    update = "UPDATE leader_assignments SET role='Gemeindevorsteher' WHERE leader_id=:l AND congregation_id=:c"
    assert await _write(sessions, people["planner_a"], update, {"l": ids["l"], "c": ids["a"]}) == 1
    assert await _write(sessions, people["planner_a"], update, {"l": ids["l"], "c": ids["b"]}) == 0  # B is not theirs
    delete = "DELETE FROM leader_assignments WHERE leader_id=:l AND congregation_id=:c"
    assert await _write(sessions, people["planner_a"], delete, {"l": ids["l"], "c": ids["b"]}) == 0
    assert await _write(sessions, people["viewer_b"], delete, {"l": ids["l"], "c": ids["b"]}) == 0  # viewers never write
    assert await _write(sessions, people["planner_district"], delete, {"l": ids["l"], "c": ids["b"]}) == 1


async def test_adding_an_assignment_needs_write_rights_for_that_congregation(sessions, world):
    ids, people = world
    insert = (
        "INSERT INTO leader_assignments (id, leader_id, district_id, congregation_id, role, is_home, created_at, updated_at) "
        "VALUES (:i, :l, :d, :c, NULL, false, now(), now())"
    )
    params = lambda c: {"i": uuid.uuid4(), "l": ids["m"], "d": ids["district"], "c": ids[c]}  # noqa: E731
    assert await _write(sessions, people["planner_a"], insert, params("a")) == 1
    with pytest.raises(DBAPIError):  # not a planner of B
        await _write(sessions, people["planner_a"], insert, params("b"))
    with pytest.raises(DBAPIError):  # a viewer of B cannot attach anyone to B
        await _write(sessions, people["viewer_b"], insert, params("b"))
    with pytest.raises(DBAPIError):  # a planner of another district cannot
        await _write(sessions, people["planner_other"], insert, params("b"))


async def test_a_congregation_planner_can_create_a_leader_and_its_assignment_together(sessions, world):
    ids, people = world
    leader_id = uuid.uuid4()
    async with sessions() as db, db.begin():
        await _as(db, people["planner_a"])
        repo = SqlLeaderRepository(db)
        leader = Leader.create(name="Neu Person", district_id=ids["district"], congregation_id=ids["a"])
        leader.id = leader_id
        leader.assignments[0].leader_id = leader_id
        await repo.save(leader)
    assert await _visible(sessions, people["planner_a"], "leaders", "id", [leader_id]) == {leader_id}
    assert await _visible(sessions, people["planner_c"], "leaders", "id", [leader_id]) == set()
    for stranger in ("planner_other", "planner_x"):  # planners of another district cannot insert here
        with pytest.raises(DBAPIError):
            async with sessions() as db, db.begin():
                await _as(db, people[stranger])
                other = Leader.create(name="Fremd", district_id=ids["district"])
                await SqlLeaderRepository(db).save(other)


async def test_leader_updates_follow_the_assigned_congregations(sessions, world):
    ids, people = world
    update = "UPDATE leaders SET notes='x' WHERE id=:l"
    assert await _write(sessions, people["planner_a"], update, {"l": ids["l"]}) == 1
    assert await _write(sessions, people["planner_c"], update, {"l": ids["l"]}) == 0  # not assigned to C
    with pytest.raises(DBAPIError):  # a viewer may read the leader, but WITH CHECK demands a planner
        await _write(sessions, people["viewer_b"], update, {"l": ids["l"]})


async def test_the_leader_insert_policy_itself_is_scoped_to_the_district(sessions, world):
    """Isolated from the assignment policy: only the leader row is inserted."""
    ids, people = world
    insert = (
        "INSERT INTO leaders (id, name, district_id, is_active, hidden_from_lists, created_at, updated_at) "
        "VALUES (:i, 'Roh', :d, true, false, now(), now())"
    )
    params = lambda: {"i": uuid.uuid4(), "d": ids["district"]}  # noqa: E731
    assert await _write(sessions, people["planner_a"], insert, params()) == 1  # congregation planner of the district
    assert await _write(sessions, people["planner_district"], insert, params()) == 1
    for denied in ("viewer_b", "planner_other", "planner_x"):
        with pytest.raises(DBAPIError):
            await _write(sessions, people[denied], insert, params())
