# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end tenant isolation through the HTTP API (real PostgreSQL with RLS).

Requests pass the full stack: tenant and CSRF middleware, OIDC authentication
(only token verification is mocked), membership loading, role guards and
repositories on the NOBYPASSRLS application role. Skipped unless configured:

    RLS_TEST_DATABASE_URL   owner DSN used to seed and inspect fixtures
    RLS_TEST_APP_PASSWORD   password of the application role
    APP_DB_USER             application role name (default: nak_app)
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.adapters.api import deps
from app.adapters.db.session import _set_tenant_gucs, get_db_session
from app.application import audit_service as audit_module

OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not (OWNER_DSN and APP_PASSWORD),
        reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
    ),
]


def _async_url(**overrides):
    return make_url(OWNER_DSN).set(drivername="postgresql+asyncpg", **overrides)


def _token(sub: str) -> str:
    """JWT-shaped token whose subject is trusted only by the mocked OIDC validator."""

    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{part({'alg': 'none'})}.{part({'sub': sub})}.sig"


@dataclass(frozen=True)
class Tenant:
    district_id: uuid.UUID
    slot_id: uuid.UUID
    leader_id: uuid.UUID
    planner_sub: str


@dataclass(frozen=True)
class World:
    a: Tenant
    b: Tenant
    run: str


@pytest.fixture
async def owner() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_async_url())
    yield engine
    await engine.dispose()


async def _seed(conn, tenant: Tenant, label: str) -> None:
    await conn.execute(
        text(
            "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, :n, now(), now())"
        ),
        {"id": tenant.district_id, "n": f"E2E {label}"},
    )
    await conn.execute(
        text(
            "INSERT INTO planning_slots (id, district_id, title, planning_date, planning_time, "
            "status, applicability, created_at, updated_at) "
            "VALUES (:id, :d, 'Gottesdienst', '2027-01-03', '09:30', 'ACTIVE', '{}', now(), now())"
        ),
        {"id": tenant.slot_id, "d": tenant.district_id},
    )
    await conn.execute(
        text("INSERT INTO leaders (id, name, district_id) VALUES (:id, :n, :d)"),
        {"id": tenant.leader_id, "n": f"Leiter {label}", "d": tenant.district_id},
    )
    await conn.execute(
        text(
            "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
            "VALUES (:id, :sub, :email, :sub, false, now(), now())"
        ),
        {
            "id": uuid.uuid4(),
            "sub": tenant.planner_sub,
            "email": f"{tenant.planner_sub}@example.org",
        },
    )
    await conn.execute(
        text(
            "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, "
            "updated_at) VALUES (:id, :sub, 'PLANNER', 'DISTRICT', :d, now(), now())"
        ),
        {"id": uuid.uuid4(), "sub": tenant.planner_sub, "d": tenant.district_id},
    )


@pytest.fixture
async def world(owner: AsyncEngine) -> AsyncIterator[World]:
    run = uuid.uuid4().hex[:8]

    def tenant(label: str) -> Tenant:
        return Tenant(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), f"e2e-{run}-planner-{label}")

    seeded = World(tenant("a"), tenant("b"), run)
    async with owner.begin() as conn:
        await _seed(conn, seeded.a, "A")
        await _seed(conn, seeded.b, "B")
    yield seeded
    districts = [seeded.a.district_id, seeded.b.district_id]
    async with owner.begin() as conn:
        for statement in (
            "DELETE FROM audit_logs WHERE user_sub LIKE :p",
            "DELETE FROM memberships WHERE user_sub LIKE :p",
            "DELETE FROM users WHERE sub LIKE :p",
        ):
            await conn.execute(text(statement), {"p": f"e2e-{run}-%"})
        for table in ("leaders", "planning_slots", "districts"):
            column = "id" if table == "districts" else "district_id"
            await conn.execute(
                text(f"DELETE FROM {table} WHERE {column} = ANY(:ids)"),  # noqa: S608
                {"ids": districts},
            )


@pytest.fixture
async def api(world: World) -> AsyncIterator[httpx.AsyncClient]:
    """API client whose database work runs as the application role."""
    from app.main import app

    engine = create_async_engine(_async_url(username=APP_ROLE, password=APP_PASSWORD))
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def db_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def claims(token: str) -> dict:
        payload = token.split(".")[1]
        sub = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["sub"]
        return {"sub": sub, "email": f"{sub}@example.org", "preferred_username": sub, "name": sub}

    oidc = AsyncMock(spec=deps.OIDCAdapter)
    oidc.validate_token.side_effect = claims
    oidc.extract_user_info.side_effect = lambda c: {
        "sub": c["sub"],
        "email": c["email"],
        "username": c["preferred_username"],
        "name": c["name"],
        "given_name": None,
        "family_name": None,
    }
    deps.set_oidc_adapter(oidc)
    app.dependency_overrides[get_db_session] = db_session
    try:
        with (
            patch("app.adapters.db.session.AsyncSessionLocal", factory),
            patch.object(audit_module, "AsyncSessionLocal", factory),
        ):
            audit_module.audit_service._queue = asyncio.Queue()
            await audit_module.audit_service.start()
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
            await audit_module.audit_service.stop()
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        deps.set_oidc_adapter(None)
        await engine.dispose()


async def _headers(client: httpx.AsyncClient, sub: str) -> dict[str, str]:
    auth = {"Authorization": f"Bearer {_token(sub)}"}
    response = await client.get("/api/v1/auth/me", headers=auth)
    assert response.status_code == 200, response.text
    return {**auth, "X-CSRF-Token": client.cookies["csrf_token"]}


async def _scalar(owner: AsyncEngine, sql: str, **params):
    async with owner.connect() as conn:
        return (await conn.execute(text(sql), params)).scalar_one_or_none()


async def test_planner_manages_leaders_in_own_district(api, owner, world) -> None:
    headers = await _headers(api, world.a.planner_sub)
    base = f"/api/v1/districts/{world.a.district_id}/leaders"

    created = await api.post(base, json={"name": "Neu"}, headers=headers)
    assert created.status_code == 201, created.text
    leader_id = created.json()["id"]
    listed = await api.get(base, headers=headers)
    assert {leader["id"] for leader in listed.json()} >= {leader_id, str(world.a.leader_id)}
    assert str(world.b.leader_id) not in {leader["id"] for leader in listed.json()}
    patched = await api.patch(f"{base}/{leader_id}", json={"name": "Umbenannt"}, headers=headers)
    assert patched.json()["name"] == "Umbenannt"
    deleted = await api.delete(f"{base}/{leader_id}", headers=headers)
    assert deleted.status_code == 204

    assert (
        await _scalar(owner, "SELECT count(*) FROM leaders WHERE id = :id", id=uuid.UUID(leader_id))
        == 0
    )

    await audit_module.audit_service.stop()
    async with owner.connect() as conn:
        trail = (
            await conn.execute(
                text(
                    "SELECT action, status FROM audit_logs WHERE resource_id = :id "
                    "ORDER BY timestamp"
                ),
                {"id": uuid.UUID(leader_id)},
            )
        ).all()
    assert trail == [("UPDATE", "SUCCESS"), ("DELETE", "SUCCESS")]


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/v1/districts/{b}/leaders"),
        ("GET", "/api/v1/districts/{b}/matrix"),
        ("POST", "/api/v1/districts/{b}/leaders"),
    ],
)
async def test_foreign_district_is_refused(api, owner, world, method, path) -> None:
    headers = await _headers(api, world.a.planner_sub)
    url = path.format(b=world.b.district_id)

    response = await api.request(
        method, url, json={"name": "Fremd"} if method == "POST" else None, headers=headers
    )

    assert response.status_code == 403
    assert (
        await _scalar(
            owner, "SELECT count(*) FROM leaders WHERE district_id = :d", d=world.b.district_id
        )
        == 1
    )


async def test_foreign_rows_are_invisible_even_via_own_district_path(api, owner, world) -> None:
    headers = await _headers(api, world.a.planner_sub)
    own_path_foreign_leader = f"/api/v1/districts/{world.a.district_id}/leaders/{world.b.leader_id}"
    foreign_leader = f"/api/v1/districts/{world.b.district_id}/leaders/{world.b.leader_id}"

    patched = await api.patch(own_path_foreign_leader, json={"name": "Gekapert"}, headers=headers)
    deleted = await api.delete(foreign_leader, headers=headers)
    event_patch = await api.patch(
        f"/api/v1/events/{world.b.slot_id}", json={"title": "Gekapert"}, headers=headers
    )

    # Foreign resources are hidden by RLS even when their identifiers are
    # supplied under a route the caller can otherwise address. A foreign
    # district path is rejected by the role guard first (403, audited).
    assert (patched.status_code, deleted.status_code, event_patch.status_code) == (404, 403, 404)
    name = await _scalar(owner, "SELECT name FROM leaders WHERE id = :id", id=world.b.leader_id)
    title = await _scalar(
        owner, "SELECT title FROM planning_slots WHERE id = :id", id=world.b.slot_id
    )
    assert (name, title) == ("Leiter B", "Gottesdienst")


async def test_event_list_only_contains_own_district(api, world) -> None:
    headers = await _headers(api, world.b.planner_sub)
    own = await api.get(
        "/api/v1/events", params={"district_id": str(world.b.district_id)}, headers=headers
    )
    foreign = await api.get(
        "/api/v1/events", params={"district_id": str(world.a.district_id)}, headers=headers
    )

    assert own.status_code == 200
    assert str(world.b.slot_id) in {item["id"] for item in own.json()["items"]}
    assert foreign.status_code == 403


async def test_denied_read_is_audited_for_the_probed_district(api, owner, world) -> None:
    headers = await _headers(api, world.a.planner_sub)
    response = await api.get(f"/api/v1/districts/{world.b.district_id}/matrix", headers=headers)
    assert response.status_code == 403
    await audit_module.audit_service.stop()

    async with owner.connect() as conn:
        rows = (
            (
                await conn.execute(
                    text(
                        "SELECT action, status, district_id, extra_metadata FROM audit_logs "
                        "WHERE action = 'ACCESS_DENIED' AND district_id = :d"
                    ),
                    {"d": world.b.district_id},
                )
            )
            .mappings()
            .all()
        )
    assert len(rows) == 1
    assert rows[0]["status"] == "FAILED"
    assert rows[0]["district_id"] == world.b.district_id
    assert rows[0]["extra_metadata"]["http_method"] == "GET"
    # Middleware must not persist identity claims extracted from an unverified bearer payload.
    assert "claimed_sub" not in rows[0]["extra_metadata"]


async def test_congregation_export_feed_contains_distributed_district_slots(
    api, owner, world
) -> None:
    """RLS lets a congregation token read applicable district slots only (#466)."""
    congregation_id = uuid.uuid4()
    token = f"e2e-{world.run}-{uuid.uuid4().hex}"
    applicable, to_all, not_applicable, foreign = (uuid.uuid4() for _ in range(4))
    slots = [
        (applicable, world.a.district_id, [str(congregation_id)]),
        (to_all, world.a.district_id, ["all"]),
        (not_applicable, world.a.district_id, [str(uuid.uuid4())]),
        (foreign, world.b.district_id, ["all", str(congregation_id)]),
    ]
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                "VALUES (:id, 'Gemeinde A', :d, now(), now())"
            ),
            {"id": congregation_id, "d": world.a.district_id},
        )
        await conn.execute(
            text(
                "INSERT INTO export_tokens (id, token, label, token_type, district_id, "
                "congregation_id) VALUES (:id, :t, 'Gemeinde A', 'PUBLIC', :d, :c)"
            ),
            {"id": uuid.uuid4(), "t": token, "d": world.a.district_id, "c": congregation_id},
        )
        for slot_id, district_id, applicability in slots:
            await conn.execute(
                text(
                    "INSERT INTO planning_slots (id, district_id, title, category, planning_date, "
                    "planning_time, status, approval_status, applicability, created_at, "
                    "updated_at) VALUES (:id, :d, 'Bezirksgottesdienst', 'Gottesdienst', "
                    "'2027-01-10', '10:00', 'ACTIVE', 'CONFIRMED', :a, now(), now())"
                ),
                {"id": slot_id, "d": district_id, "a": applicability},
            )
    try:
        response = await api.get(f"/api/v1/export/{token}/calendar.ics")
    finally:
        async with owner.begin() as conn:
            await conn.execute(text("DELETE FROM export_tokens WHERE token = :t"), {"t": token})
            await conn.execute(
                text("DELETE FROM planning_slots WHERE id = ANY(:ids)"),
                {"ids": [slot_id for slot_id, _, _ in slots]},
            )
            await conn.execute(
                text("DELETE FROM congregations WHERE id = :id"), {"id": congregation_id}
            )

    assert response.status_code == 200, response.text
    body = response.text
    assert f"UID:{applicable}@nak-bezirksplaner" in body
    assert f"UID:{to_all}@nak-bezirksplaner" in body
    assert str(not_applicable) not in body
    assert str(foreign) not in body


@pytest.mark.parametrize(
    ("token_type", "personal", "expected_comment"),
    [
        ("INTERNAL", False, "Dienstleiter: Leiter Export"),
        ("PUBLIC", True, "Dienstleiter: Leiter Export"),
        ("PUBLIC", False, "Dienstleiter: [Name anonymisiert]"),
    ],
)
async def test_export_feed_resolves_leader_names_under_rls(
    api, owner, world, token_type, personal, expected_comment
) -> None:
    """Export tokens read only the leaders their feed names (#485)."""
    leader_id, slot_id = uuid.uuid4(), uuid.uuid4()
    token = f"e2e-{world.run}-{uuid.uuid4().hex}"
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO leaders (id, name, district_id) VALUES (:id, 'Leiter Export', :d)"
            ),
            {"id": leader_id, "d": world.a.district_id},
        )
        await conn.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, title, category, planning_date, "
                "planning_time, status, approval_status, applicability, created_at, updated_at) "
                "VALUES (:id, :d, 'Gottesdienst', 'Gottesdienst', '2027-01-10', '10:00', "
                "'ACTIVE', 'CONFIRMED', '{}', now(), now())"
            ),
            {"id": slot_id, "d": world.a.district_id},
        )
        await conn.execute(
            text(
                "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_id, "
                "status, created_at, updated_at) "
                "VALUES (:id, :s, :s, :l, 'ASSIGNED', now(), now())"
            ),
            {"id": uuid.uuid4(), "s": slot_id, "l": leader_id},
        )
        await conn.execute(
            text(
                "INSERT INTO export_tokens (id, token, label, token_type, district_id, leader_id) "
                "VALUES (:id, :t, 'Feed', :tt, :d, :l)"
            ),
            {
                "id": uuid.uuid4(),
                "t": token,
                "tt": token_type,
                "d": world.a.district_id,
                "l": leader_id if personal else None,
            },
        )
    try:
        response = await api.get(f"/api/v1/export/{token}/calendar.ics")
    finally:
        async with owner.begin() as conn:
            await conn.execute(text("DELETE FROM export_tokens WHERE token = :t"), {"t": token})
            await conn.execute(text("DELETE FROM planning_slots WHERE id = :id"), {"id": slot_id})
            await conn.execute(text("DELETE FROM leaders WHERE id = :id"), {"id": leader_id})

    assert response.status_code == 200, response.text
    assert f"UID:{slot_id}@nak-bezirksplaner" in response.text
    assert expected_comment in response.text
    if expected_comment.endswith("[Name anonymisiert]"):
        assert "Leiter Export" not in response.text
