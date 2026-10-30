# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Memberships per unit and superadmin appointment under the application role.

Covers revisions ``20261030_membership_scope_unique`` and
``20261030_superadmin_appointment``: duplicate consolidation, atomic upserts,
administrators reading the memberships they manage, the one-time bootstrap
grant and ``set_user_superadmin`` including the last-superadmin lock.
Skipped unless ``RLS_TEST_DATABASE_URL`` and ``RLS_TEST_APP_PASSWORD`` are set.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.adapters.db.repositories.membership import SqlMembershipRepository
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role

OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = pytest.mark.skipif(
    not (OWNER_DSN and APP_PASSWORD),
    reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
)

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261030_membership_scope_unique.py"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location("membership_scope_unique", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _url(**overrides):
    return make_url(OWNER_DSN).set(drivername="postgresql+asyncpg", **overrides)


@pytest.fixture
async def owner() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_url())
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_url(username=APP_ROLE, password=APP_PASSWORD))
    yield engine
    await engine.dispose()


@pytest.fixture
async def world(owner: AsyncEngine) -> AsyncIterator[dict]:
    """Two districts with one congregation each, and a handful of users.

    Superadmins already in the database are switched off for the test, so
    the last-superadmin rules see only this test's accounts, and restored
    afterwards, as is the bootstrap configuration.
    """
    tag = uuid.uuid4().hex[:8]
    ids = {
        "d1": uuid.uuid4(),
        "d2": uuid.uuid4(),
        "c1": uuid.uuid4(),
        "c2": uuid.uuid4(),
    }
    subs = {name: f"{name}-{tag}" for name in ("admin", "member", "root", "other", "outsider")}
    async with owner.begin() as conn:
        previous = (
            (await conn.execute(text("SELECT sub FROM users WHERE is_superadmin"))).scalars().all()
        )
        config = (
            await conn.execute(
                text(
                    "SELECT superadmin_sub, bootstrap_completed_at FROM app_superadmin_config WHERE id = 1"
                )
            )
        ).one()
        await conn.execute(text("UPDATE users SET is_superadmin = false WHERE is_superadmin"))
        for key in ("d1", "d2"):
            await conn.execute(
                text(
                    "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, :n, now(), now())"
                ),
                {"i": ids[key], "n": f"M {key} {tag}"},
            )
        for key, district in (("c1", "d1"), ("c2", "d2")):
            await conn.execute(
                text(
                    "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                    "VALUES (:i, :n, :d, now(), now())"
                ),
                {"i": ids[key], "n": f"M {key} {tag}", "d": ids[district]},
            )
        for name, sub in subs.items():
            await conn.execute(
                text(
                    "INSERT INTO users (id, sub, email, username, created_at, updated_at, is_superadmin) "
                    "VALUES (:i, :s, :e, :s, now(), now(), :sa)"
                ),
                {"i": uuid.uuid4(), "s": sub, "e": f"{sub}@example.org", "sa": name == "root"},
            )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) "
                "VALUES (:i, :s, 'DISTRICT_ADMIN', 'DISTRICT', :d, now(), now())"
            ),
            {"i": uuid.uuid4(), "s": subs["admin"], "d": ids["d1"]},
        )
    yield {**ids, "subs": subs}
    async with owner.begin() as conn:
        await conn.execute(
            text("DELETE FROM memberships WHERE user_sub = ANY(:s)"), {"s": list(subs.values())}
        )
        await conn.execute(
            text("DELETE FROM users WHERE sub = ANY(:s)"), {"s": list(subs.values())}
        )
        await conn.execute(
            text("DELETE FROM congregations WHERE id IN (:a, :b)"), {"a": ids["c1"], "b": ids["c2"]}
        )
        await conn.execute(
            text("DELETE FROM districts WHERE id IN (:a, :b)"), {"a": ids["d1"], "b": ids["d2"]}
        )
        await conn.execute(
            text("UPDATE users SET is_superadmin = true WHERE sub = ANY(:s)"), {"s": list(previous)}
        )
        await conn.execute(
            text(
                "UPDATE app_superadmin_config SET superadmin_sub = :s, bootstrap_completed_at = :c WHERE id = 1"
            ),
            {"s": config.superadmin_sub, "c": config.bootstrap_completed_at},
        )


async def _as(app_engine: AsyncEngine, sub: str, sql: str, params: dict | None = None):
    """Run one statement in its own transaction as ``sub`` under the app role."""
    async with app_engine.begin() as conn:
        await conn.execute(text("SELECT set_config('app.current_user_sub', :s, true)"), {"s": sub})
        return (await conn.execute(text(sql), params or {})).all()


async def _set_superadmin(app_engine, actor: str, target: str, value: bool) -> str:
    rows = await _as(
        app_engine, actor, "SELECT set_user_superadmin(:t, :v)", {"t": target, "v": value}
    )
    return rows[0][0]


async def _is_superadmin(owner: AsyncEngine, sub: str) -> bool:
    async with owner.connect() as conn:
        return (
            await conn.execute(text("SELECT is_superadmin FROM users WHERE sub = :s"), {"s": sub})
        ).scalar_one()


# --- memberships -----------------------------------------------------------


async def test_duplicates_collapse_to_the_highest_role_and_are_archived(owner, world) -> None:
    """The migration's consolidation keeps the highest role and archives the rest."""
    migration = _migration_module()
    member = world["subs"]["member"]
    other_scope = world["c2"]
    async with owner.connect() as conn:
        tx = await conn.begin()
        try:
            await conn.execute(
                text(f"ALTER TABLE memberships DROP CONSTRAINT {migration.NEW_CONSTRAINT}")
            )
            for role, scope_type, scope_id in (
                ("VIEWER", "CONGREGATION", world["c1"]),
                ("PLANNER", "CONGREGATION", world["c1"]),
                ("VIEWER", "CONGREGATION", world["c1"]),
                ("VIEWER", "CONGREGATION", other_scope),
            ):
                await conn.execute(
                    text(
                        "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) "
                        "VALUES (:i, :s, :r, :t, :c, now(), now())"
                    ),
                    {"i": uuid.uuid4(), "s": member, "r": role, "t": scope_type, "c": scope_id},
                )
            await conn.execute(text(migration.ARCHIVE_DUPLICATES_SQL))
            await conn.execute(text(migration.DELETE_DUPLICATES_SQL))
            kept = (
                await conn.execute(
                    text(
                        "SELECT role, scope_id FROM memberships WHERE user_sub = :s ORDER BY role"
                    ),
                    {"s": member},
                )
            ).all()
            archived = (
                (
                    await conn.execute(
                        text(f"SELECT role FROM {migration.ARCHIVE_TABLE} WHERE user_sub = :s"),
                        {"s": member},
                    )
                )
                .scalars()
                .all()
            )
        finally:
            await tx.rollback()

    assert sorted(kept) == sorted([("PLANNER", world["c1"]), ("VIEWER", other_scope)])
    assert sorted(archived) == ["VIEWER", "VIEWER"]


async def test_concurrent_upserts_of_one_unit_leave_one_row(app_engine, world) -> None:
    sessions = async_sessionmaker(app_engine, expire_on_commit=False)
    member = world["subs"]["member"]

    async def assign(role: Role) -> None:
        async with sessions() as session, session.begin():
            await session.execute(
                text("SELECT set_config('app.current_user_sub', :s, true)"),
                {"s": world["subs"]["root"]},
            )
            await SqlMembershipRepository(session).upsert_by_scope(
                user_sub=member, scope_type=ScopeType.CONGREGATION, scope_id=world["c1"], role=role
            )

    await asyncio.gather(assign(Role.VIEWER), assign(Role.PLANNER), assign(Role.VIEWER))
    await assign(Role.PLANNER)
    rows = await _as(
        app_engine,
        world["subs"]["root"],
        "SELECT role FROM memberships WHERE user_sub = :s AND scope_id = :c",
        {"s": member, "c": world["c1"]},
    )
    assert rows == [("PLANNER",)]


async def test_second_unit_keeps_the_first(app_engine, world) -> None:
    sessions = async_sessionmaker(app_engine, expire_on_commit=False)
    member = world["subs"]["member"]
    async with sessions() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_user_sub', :s, true)"),
            {"s": world["subs"]["root"]},
        )
        repo = SqlMembershipRepository(session)
        await repo.upsert_by_scope(
            user_sub=member,
            scope_type=ScopeType.CONGREGATION,
            scope_id=world["c1"],
            role=Role.VIEWER,
        )
        await repo.upsert_by_scope(
            user_sub=member, scope_type=ScopeType.DISTRICT, scope_id=world["d2"], role=Role.PLANNER
        )
        memberships = await repo.get_all_by_user(member)
    assert {(m.scope_id, m.role) for m in memberships} == {
        (world["c1"], Role.VIEWER),
        (world["d2"], Role.PLANNER),
    }


async def test_administrator_reads_memberships_of_managed_units_only(
    owner, app_engine, world
) -> None:
    member = world["subs"]["member"]
    async with owner.begin() as conn:
        for scope_type, scope_id in (("CONGREGATION", world["c1"]), ("CONGREGATION", world["c2"])):
            await conn.execute(
                text(
                    "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) "
                    "VALUES (:i, :s, 'VIEWER', :t, :c, now(), now())"
                ),
                {"i": uuid.uuid4(), "s": member, "t": scope_type, "c": scope_id},
            )
    sql = "SELECT scope_id FROM memberships WHERE user_sub = :s"
    admin_view = await _as(app_engine, world["subs"]["admin"], sql, {"s": member})
    outsider_view = await _as(app_engine, world["subs"]["outsider"], sql, {"s": member})
    own_view = await _as(app_engine, member, sql, {"s": member})

    assert [row[0] for row in admin_view] == [world["c1"]]
    assert outsider_view == []
    assert {row[0] for row in own_view} == {world["c1"], world["c2"]}


# --- superadmin appointment ------------------------------------------------


async def test_superadmin_appoints_and_revokes(owner, app_engine, world) -> None:
    root, other = world["subs"]["root"], world["subs"]["other"]
    assert await _set_superadmin(app_engine, root, other, True) == "granted"
    assert await _is_superadmin(owner, other) is True
    assert await _set_superadmin(app_engine, root, other, True) == "unchanged"
    assert await _set_superadmin(app_engine, other, root, False) == "revoked"
    assert await _is_superadmin(owner, root) is False


@pytest.mark.parametrize("actor", ["admin", "outsider"])
async def test_non_superadmin_cannot_appoint(owner, app_engine, world, actor) -> None:
    target = world["subs"]["member"]
    assert await _set_superadmin(app_engine, world["subs"][actor], target, True) == "forbidden"
    assert await _is_superadmin(owner, target) is False


async def test_self_appointment_by_non_superadmin_is_forbidden(owner, app_engine, world) -> None:
    member = world["subs"]["member"]
    assert await _set_superadmin(app_engine, member, member, True) == "forbidden"
    assert await _is_superadmin(owner, member) is False


async def test_unknown_target_and_missing_subject(app_engine, world) -> None:
    assert (
        await _set_superadmin(app_engine, world["subs"]["root"], "nobody-" + uuid.uuid4().hex, True)
        == "not_found"
    )
    with pytest.raises(Exception, match="authenticated subject"):
        await _as(
            app_engine, "", "SELECT set_user_superadmin(:t, true)", {"t": world["subs"]["member"]}
        )


async def test_last_superadmin_cannot_be_revoked(owner, app_engine, world) -> None:
    root = world["subs"]["root"]
    assert await _set_superadmin(app_engine, root, root, False) == "last_superadmin"
    assert await _is_superadmin(owner, root) is True


async def test_concurrent_mutual_revocation_keeps_one_superadmin(owner, app_engine, world) -> None:
    root, other = world["subs"]["root"], world["subs"]["other"]
    assert await _set_superadmin(app_engine, root, other, True) == "granted"

    results = await asyncio.gather(
        _set_superadmin(app_engine, root, other, False),
        _set_superadmin(app_engine, other, root, False),
    )

    assert sorted(results) in (["forbidden", "revoked"], ["last_superadmin", "revoked"])
    remaining = [sub for sub in (root, other) if await _is_superadmin(owner, sub)]
    assert len(remaining) == 1


async def test_app_role_cannot_write_the_flag_directly(app_engine, world) -> None:
    with pytest.raises(Exception, match="permission denied"):
        await _as(
            app_engine,
            world["subs"]["member"],
            "UPDATE users SET is_superadmin = true WHERE sub = :s",
            {"s": world["subs"]["member"]},
        )


# --- one-time bootstrap ----------------------------------------------------


async def _configure_bootstrap(owner: AsyncEngine, sub: str) -> None:
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "UPDATE app_superadmin_config SET superadmin_sub = :s, bootstrap_completed_at = NULL WHERE id = 1"
            ),
            {"s": sub},
        )


async def _login(app_engine: AsyncEngine, sub: str) -> bool:
    rows = await _as(app_engine, sub, "SELECT grant_bootstrap_superadmin(:s)", {"s": sub})
    return rows[0][0]


async def test_bootstrap_grants_once_and_never_resets_later_decisions(
    owner, app_engine, world
) -> None:
    root, member, other = world["subs"]["root"], world["subs"]["member"], world["subs"]["other"]
    await _configure_bootstrap(owner, member)

    assert await _login(app_engine, other) is False  # unrelated subject: nothing happens
    assert await _login(app_engine, member) is True
    async with owner.connect() as conn:
        completed = (
            await conn.execute(
                text("SELECT bootstrap_completed_at FROM app_superadmin_config WHERE id = 1")
            )
        ).scalar_one()
    assert completed is not None

    # An appointed superadmin survives the bootstrap subject's next login.
    assert await _set_superadmin(app_engine, member, other, True) == "granted"
    assert await _login(app_engine, member) is True
    assert await _is_superadmin(owner, other) is True
    assert await _is_superadmin(owner, root) is True

    # A revoked bootstrap subject stays revoked across logins.
    assert await _set_superadmin(app_engine, other, member, False) == "revoked"
    assert await _login(app_engine, member) is False
    assert await _is_superadmin(owner, member) is False


async def test_bootstrap_without_configured_subject_grants_nothing(
    owner, app_engine, world
) -> None:
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "UPDATE app_superadmin_config SET superadmin_sub = NULL, bootstrap_completed_at = NULL WHERE id = 1"
            )
        )
    member = world["subs"]["member"]
    assert await _login(app_engine, member) is False
    assert await _is_superadmin(owner, member) is False


async def test_bootstrap_rejects_a_foreign_subject(app_engine, world) -> None:
    with pytest.raises(Exception, match="does not match authenticated subject"):
        await _as(
            app_engine,
            world["subs"]["member"],
            "SELECT grant_bootstrap_superadmin(:s)",
            {"s": world["subs"]["root"]},
        )


async def _upsert_as(app_engine, actor: str, **kwargs) -> None:
    sessions = async_sessionmaker(app_engine, expire_on_commit=False)
    async with sessions() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_user_sub', :s, true)"), {"s": actor}
        )
        await SqlMembershipRepository(session).upsert_by_scope(**kwargs)


async def test_district_admin_assigns_inside_and_not_outside(app_engine, world) -> None:
    """Admin-path INSERT works under the app role (it used to hit policy recursion)."""
    member = world["subs"]["member"]
    await _upsert_as(
        app_engine,
        world["subs"]["admin"],
        user_sub=member,
        scope_type=ScopeType.CONGREGATION,
        scope_id=world["c1"],
        role=Role.PLANNER,
    )
    with pytest.raises(Exception, match="row-level security"):
        await _upsert_as(
            app_engine,
            world["subs"]["admin"],
            user_sub=member,
            scope_type=ScopeType.CONGREGATION,
            scope_id=world["c2"],
            role=Role.PLANNER,
        )
    rows = await _as(
        app_engine,
        member,
        "SELECT scope_id, role FROM memberships WHERE user_sub = :s",
        {"s": member},
    )
    assert rows == [(world["c1"], "PLANNER")]


async def test_user_inserts_own_membership_only_from_an_approved_registration(
    owner, app_engine, world
) -> None:
    member = world["subs"]["member"]
    registration_id = uuid.uuid4()
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO leader_registrations (id, district_id, name, email, status, user_sub, "
                "assigned_role, assigned_scope_type, assigned_scope_id, created_at, updated_at) "
                "VALUES (:i, :d, 'Member', :e, 'APPROVED', :s, 'VIEWER', 'CONGREGATION', :c, now(), now())"
            ),
            {
                "i": registration_id,
                "d": world["d1"],
                "e": f"{member}@example.org",
                "s": member,
                "c": world["c1"],
            },
        )
    try:
        await _upsert_as(
            app_engine,
            member,
            user_sub=member,
            scope_type=ScopeType.CONGREGATION,
            scope_id=world["c1"],
            role=Role.VIEWER,
        )
        with pytest.raises(Exception, match="row-level security"):
            await _upsert_as(
                app_engine,
                member,
                user_sub=member,
                scope_type=ScopeType.CONGREGATION,
                scope_id=world["c1"],
                role=Role.PLANNER,
            )
    finally:
        async with owner.begin() as conn:
            await conn.execute(
                text("DELETE FROM leader_registrations WHERE id = :i"), {"i": registration_id}
            )


# --- user administration API ------------------------------------------------


async def _api(app_engine, owner, actor: str, handler, **kwargs):
    """Call a users router handler like a request of ``actor``: one session, then commit."""
    from fastapi import HTTPException
    from sqlalchemy import event

    from app.adapters.api.deps import CurrentUserContext
    from app.adapters.api.routers import users as users_router
    from app.adapters.db.repositories.congregation import SqlCongregationRepository
    from app.adapters.db.repositories.district import SqlDistrictRepository
    from app.adapters.db.repositories.user import SqlUserRepository
    from app.adapters.db.session import AuditedSession, _set_tenant_gucs
    from app.tenant import TenantContext

    event.listen(app_engine.sync_engine, "begin", _set_tenant_gucs)
    sessions = async_sessionmaker(
        app_engine, expire_on_commit=False, sync_session_class=AuditedSession
    )
    TenantContext.set_context(user_sub=actor)
    try:
        async with sessions() as session:
            user = await SqlUserRepository(session).get_by_sub(actor)
            memberships = await SqlMembershipRepository(session).get_all_by_user(actor)
            auth = CurrentUserContext(user=user, memberships=memberships)
            repos = {
                "user_repo": SqlUserRepository(session),
                "membership_repo": SqlMembershipRepository(session),
                "district_repo": SqlDistrictRepository(session),
                "congregation_repo": SqlCongregationRepository(session),
            }
            func = getattr(users_router, handler)
            params = __import__("inspect").signature(func).parameters
            call = {k: v for k, v in repos.items() if k in params}
            if "db" in params:
                call["db"] = session
            try:
                result = await func(auth=auth, **call, **kwargs)
            except HTTPException:
                await session.rollback()
                raise
            await session.commit()
            return result
    finally:
        TenantContext.clear_context()
        event.remove(app_engine.sync_engine, "begin", _set_tenant_gucs)


async def _audit_count(owner, resource_type: str, actor: str) -> int:
    async with owner.connect() as conn:
        return await conn.scalar(
            text("SELECT count(*) FROM audit_logs WHERE resource_type = :t AND user_sub = :s"),
            {"t": resource_type, "s": actor},
        )


async def test_api_district_admin_adds_second_unit_and_removes_one(
    owner, app_engine, world
) -> None:
    from app.adapters.api.schemas.user_admin import MembershipAssign

    admin, member = world["subs"]["admin"], world["subs"]["member"]
    await _api(
        app_engine,
        owner,
        admin,
        "assign_membership",
        sub=member,
        body=MembershipAssign(
            scope_type=ScopeType.CONGREGATION, scope_id=world["c1"], role=Role.VIEWER
        ),
    )
    out = await _api(
        app_engine,
        owner,
        admin,
        "assign_membership",
        sub=member,
        body=MembershipAssign(
            scope_type=ScopeType.DISTRICT, scope_id=world["d1"], role=Role.PLANNER
        ),
    )
    assert {(m.scope_id, m.role) for m in out.memberships} == {
        (world["c1"], Role.VIEWER),
        (world["d1"], Role.PLANNER),
    }
    assert out.is_superadmin is None  # hidden from non-superadmins
    assert await _audit_count(owner, "membership", admin) == 2

    removed = next(m for m in out.memberships if m.scope_id == world["c1"])
    await _api(app_engine, owner, admin, "remove_membership", sub=member, membership_id=removed.id)
    listed = await _api(app_engine, owner, admin, "list_users")
    member_row = next(u for u in listed if u.sub == member)
    assert [(m.scope_id, m.role) for m in member_row.memberships] == [(world["d1"], Role.PLANNER)]
    assert await _audit_count(owner, "membership", admin) == 3


async def test_api_rejects_units_outside_the_admins_authority(owner, app_engine, world) -> None:
    from fastapi import HTTPException

    from app.adapters.api.schemas.user_admin import MembershipAssign

    admin, member = world["subs"]["admin"], world["subs"]["member"]
    with pytest.raises(HTTPException) as foreign:
        await _api(
            app_engine,
            owner,
            admin,
            "assign_membership",
            sub=member,
            body=MembershipAssign(
                scope_type=ScopeType.CONGREGATION, scope_id=world["c2"], role=Role.VIEWER
            ),
        )
    # The foreign district's congregation is not even readable: 404 like an unknown unit.
    assert foreign.value.status_code in (403, 404)
    rows = await _as(
        app_engine,
        world["subs"]["root"],
        "SELECT 1 FROM memberships WHERE user_sub = :s",
        {"s": member},
    )
    assert rows == []


async def test_api_congregation_admin_cannot_grant_district_roles(owner, app_engine, world) -> None:
    from fastapi import HTTPException

    from app.adapters.api.schemas.user_admin import MembershipAssign

    member, outsider = world["subs"]["member"], world["subs"]["outsider"]
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) "
                "VALUES (:i, :s, 'CONGREGATION_ADMIN', 'CONGREGATION', :c, now(), now())"
            ),
            {"i": uuid.uuid4(), "s": outsider, "c": world["c1"]},
        )
    with pytest.raises(HTTPException) as exc:
        await _api(
            app_engine,
            owner,
            outsider,
            "assign_membership",
            sub=member,
            body=MembershipAssign(
                scope_type=ScopeType.DISTRICT, scope_id=world["d1"], role=Role.VIEWER
            ),
        )
    assert exc.value.status_code == 403
    out = await _api(
        app_engine,
        owner,
        outsider,
        "assign_membership",
        sub=member,
        body=MembershipAssign(
            scope_type=ScopeType.CONGREGATION, scope_id=world["c1"], role=Role.PLANNER
        ),
    )
    assert [(m.scope_id, m.role) for m in out.memberships] == [(world["c1"], Role.PLANNER)]


async def test_api_superadmin_appoints_and_cannot_revoke_the_last(owner, app_engine, world) -> None:
    from fastapi import HTTPException

    from app.adapters.api.schemas.user_admin import SuperadminUpdate

    root, other, admin = world["subs"]["root"], world["subs"]["other"], world["subs"]["admin"]
    out = await _api(
        app_engine,
        owner,
        root,
        "set_superadmin",
        sub=other,
        body=SuperadminUpdate(is_superadmin=True),
    )
    assert out.is_superadmin is True
    assert await _audit_count(owner, "user_superadmin", root) == 1

    with pytest.raises(HTTPException) as denied:
        await _api(
            app_engine,
            owner,
            admin,
            "set_superadmin",
            sub=admin,
            body=SuperadminUpdate(is_superadmin=True),
        )
    assert denied.value.status_code == 403

    # Self-revocation works while another superadmin remains, and is audited.
    await _api(
        app_engine,
        owner,
        root,
        "set_superadmin",
        sub=root,
        body=SuperadminUpdate(is_superadmin=False),
    )
    assert await _is_superadmin(owner, root) is False
    assert await _audit_count(owner, "user_superadmin", root) == 2

    with pytest.raises(HTTPException) as last:
        await _api(
            app_engine,
            owner,
            other,
            "set_superadmin",
            sub=other,
            body=SuperadminUpdate(is_superadmin=False),
        )
    assert last.value.status_code == 409
    assert await _is_superadmin(owner, other) is True
    assert await _audit_count(owner, "user_superadmin", other) == 0  # rolled back with the refusal


async def test_api_superadmin_lists_users_without_memberships(owner, app_engine, world) -> None:
    listed = await _api(app_engine, owner, world["subs"]["root"], "list_users")
    subs = {u.sub for u in listed}
    assert set(world["subs"].values()) <= subs
    root_row = next(u for u in listed if u.sub == world["subs"]["root"])
    assert root_row.is_superadmin is True


async def test_api_planner_has_no_user_administration(owner, app_engine, world) -> None:
    from fastapi import HTTPException

    member = world["subs"]["member"]
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) "
                "VALUES (:i, :s, 'PLANNER', 'DISTRICT', :d, now(), now())"
            ),
            {"i": uuid.uuid4(), "s": member, "d": world["d1"]},
        )
    with pytest.raises(HTTPException) as exc:
        await _api(app_engine, owner, member, "list_users")
    assert exc.value.status_code == 403
