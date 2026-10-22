# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""HTTP audit against a real, migrated PostgreSQL with active RLS (#648).

The application stack is the real one: ``AuditMiddleware``, the audited session
dependency, ``get_db_session`` and the audit service, all running as the
NOBYPASSRLS application role. Only the routes are test routes. Skipped unless
``RLS_TEST_DATABASE_URL`` and ``RLS_TEST_APP_PASSWORD`` are configured.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.adapters.api import deps
from app.adapters.api.middleware.audit import AuditMiddleware
from app.adapters.db import session as session_module
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.session import AuditedSession, _set_tenant_gucs
from app.application import audit_service as audit_service_module
from app.application.audit_service import AuditService
from app.domain.models.planning_slot import PlanningSlotStatus
from app.tenant import TenantContext

OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = pytest.mark.skipif(
    not (OWNER_DSN and APP_PASSWORD),
    reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
)


def _async_url(**overrides):
    return make_url(OWNER_DSN).set(drivername="postgresql+asyncpg", **overrides)


@dataclass(frozen=True)
class World:
    run: str
    district_id: uuid.UUID
    table: str  # plain table without RLS and without domain audit
    child: str  # references `table` through a deferred FK (fails only at COMMIT)

    @property
    def sub(self) -> str:
        return f"httpaudit-{self.run}-planner"


@pytest.fixture
async def owner() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_async_url())
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_async_url(username=APP_ROLE, password=APP_PASSWORD))
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    yield engine
    await engine.dispose()


@pytest.fixture
async def world(owner: AsyncEngine) -> AsyncIterator[World]:
    run = uuid.uuid4().hex[:8]
    w = World(run, uuid.uuid4(), f"http_audit_t_{run}", f"http_audit_c_{run}")
    async with owner.begin() as conn:
        await conn.execute(
            text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, :n, now(), now())"),
            {"id": w.district_id, "n": f"HTTP audit {run}"},
        )
        await conn.execute(
            text(
                "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
                "VALUES (:id, :sub, :email, :sub, false, now(), now())"
            ),
            {"id": uuid.uuid4(), "sub": w.sub, "email": f"{w.sub}@example.org"},
        )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at) "
                "VALUES (:id, :sub, 'PLANNER', 'DISTRICT', :d, now(), now())"
            ),
            {"id": uuid.uuid4(), "sub": w.sub, "d": w.district_id},
        )
        await conn.execute(text(f"CREATE TABLE {w.table} (id int PRIMARY KEY)"))
        await conn.execute(
            text(
                f"CREATE TABLE {w.child} (id int PRIMARY KEY, parent_id int REFERENCES {w.table}(id) "
                "DEFERRABLE INITIALLY DEFERRED)"
            )
        )
        await conn.execute(text(f'GRANT ALL ON {w.table}, {w.child} TO "{APP_ROLE}"'))
    yield w
    async with owner.begin() as conn:
        await conn.execute(text("DELETE FROM audit_logs WHERE district_id = :d"), {"d": w.district_id})
        await conn.execute(text("DELETE FROM planning_slots WHERE district_id = :d"), {"d": w.district_id})
        await conn.execute(text("DELETE FROM memberships WHERE user_sub = :s"), {"s": w.sub})
        await conn.execute(text("DELETE FROM users WHERE sub = :s"), {"s": w.sub})
        await conn.execute(text("DELETE FROM districts WHERE id = :d"), {"d": w.district_id})
        await conn.execute(text(f"DROP TABLE {w.child}"))
        await conn.execute(text(f"DROP TABLE {w.table}"))


@pytest.fixture
def stack(app_engine, world, monkeypatch):
    """The real session and audit plumbing on the application role."""
    factory = async_sessionmaker(app_engine, expire_on_commit=False, sync_session_class=AuditedSession)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", factory)
    monkeypatch.setattr(audit_service_module, "AsyncSessionLocal", factory)

    async def actor(request: Request) -> None:
        # What authentication does: identify the user for the request and for RLS.
        request.state.user = SimpleNamespace(sub=world.sub, email=f"{world.sub}@example.org")
        request.state.district_id = world.district_id  # what the tenant middleware provides
        TenantContext.set_context(user_sub=world.sub, user_roles=["PLANNER"])

    app = FastAPI()
    app.add_middleware(AuditMiddleware, audit_service=AuditService())
    base = f"/api/v1/districts/{world.district_id}"

    @app.post(base + "/events")
    async def write(db: deps.DbSession, _=Depends(actor)):
        await db.execute(text(f"INSERT INTO {world.table} VALUES (1)"))  # noqa: S608
        return {"ok": True}

    @app.post(base + "/broken-things")
    async def write_then_commit_fails(db: deps.DbSession, _=Depends(actor)):
        await db.execute(text(f"INSERT INTO {world.child} VALUES (1, 999)"))  # noqa: S608
        return {"ok": True}

    @app.post(base + "/rejected")
    async def write_then_reject(db: deps.DbSession, _=Depends(actor)):
        await db.execute(text(f"INSERT INTO {world.table} VALUES (2)"))  # noqa: S608
        raise HTTPException(status_code=422, detail="rejected")

    @app.get(base + "/secret")
    async def forbidden(_=Depends(actor)):
        raise HTTPException(status_code=403, detail="no access")

    @app.post(base + "/slots")
    async def write_audited_aggregate(db: deps.DbSession, _=Depends(actor)):
        now = datetime.now(UTC)
        db.add(
            PlanningSlotORM(
                id=uuid.uuid4(), district_id=world.district_id, title="Gottesdienst",
                planning_date=date(2026, 12, 25), planning_time=time(9, 30),
                status=PlanningSlotStatus.ACTIVE, applicability=[], created_at=now, updated_at=now,
            )
        )
        return {"ok": True}

    @app.get(base + "/read")
    async def read(db: deps.DbSession, _=Depends(actor)):
        await db.execute(text("SELECT 1"))
        return {"ok": True}

    async def actor_without_tenant(request: Request) -> None:
        request.state.user = SimpleNamespace(sub=world.sub, email=f"{world.sub}@example.org")
        TenantContext.set_context(user_sub=world.sub, user_roles=["PLANNER"])

    @app.post("/api/v1/standalone-events")
    async def write_without_tenant(db: deps.DbSession, _=Depends(actor_without_tenant)):
        await db.execute(text(f"INSERT INTO {world.table} VALUES (3)"))  # noqa: S608
        return {"ok": True}

    yield app, base
    TenantContext.clear_context()


async def _request(app: FastAPI, method: str, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


async def _audit(owner: AsyncEngine, world: World) -> list:
    async with owner.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT action, status, user_sub, resource_type, district_id, extra_metadata FROM audit_logs "
                "WHERE district_id = :d ORDER BY timestamp"
            ),
            {"d": world.district_id},
        )
        return list(result.mappings())


async def _rows(owner: AsyncEngine, table: str) -> int:
    async with owner.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()  # noqa: S608


async def test_a_write_without_domain_audit_commits_its_http_entry_with_the_change(owner, world, stack):
    app, base = stack

    response = await _request(app, "POST", base + "/events")

    assert response.status_code == 200
    assert await _rows(owner, world.table) == 1
    (entry,) = await _audit(owner, world)
    assert (entry["action"], entry["status"], entry["user_sub"]) == ("CREATE", "SUCCESS", world.sub)
    assert entry["resource_type"] == "districts"  # first path segment when no id is in the path
    assert entry["extra_metadata"]["http_method"] == "POST"


async def test_a_rejected_commit_leaves_neither_the_change_nor_an_audit_entry(owner, world, stack):
    app, base = stack

    response = await _request(app, "POST", base + "/broken-things")

    assert response.status_code == 500
    assert await _rows(owner, world.child) == 0
    entries = await _audit(owner, world)
    # The failed request is recorded as a failure, never as a success.
    assert [e["status"] for e in entries] == ["FAILED"]


async def test_a_write_with_a_domain_audit_entry_gets_no_second_http_entry(owner, world, stack):
    app, base = stack

    response = await _request(app, "POST", base + "/slots")

    assert response.status_code == 200
    entries = await _audit(owner, world)
    assert [e["extra_metadata"] for e in entries] == [{"source": "domain"}]


async def test_a_failed_write_is_recorded_and_its_change_rolled_back(owner, world, stack):
    app, base = stack

    response = await _request(app, "POST", base + "/rejected")

    assert response.status_code == 422
    assert await _rows(owner, world.table) == 0
    (entry,) = await _audit(owner, world)
    assert entry["status"] == "FAILED"
    assert entry["extra_metadata"]["status_code"] == 422


async def test_a_denied_request_is_durably_recorded_before_the_response(owner, world, stack):
    app, base = stack

    response = await _request(app, "GET", base + "/secret")

    assert response.status_code == 403
    (entry,) = await _audit(owner, world)
    assert entry["action"] == "ACCESS_DENIED"


async def test_a_denial_that_cannot_be_recorded_is_answered_with_503(owner, world, stack, monkeypatch):
    app, base = stack

    def unavailable():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(audit_service_module, "AsyncSessionLocal", unavailable)

    response = await _request(app, "GET", base + "/secret")

    assert response.status_code == 503
    assert "Audit" in response.json()["detail"]
    assert await _audit(owner, world) == []


async def test_successful_reads_are_not_audited(owner, world, stack):
    app, base = stack

    response = await _request(app, "GET", base + "/read")

    assert response.status_code == 200
    assert await _audit(owner, world) == []


async def test_a_write_without_tenant_still_gets_its_entry_despite_row_level_security(owner, world, stack):
    """The audit_logs policy needs a tenant; the entry insert runs as the system worker."""
    app, _ = stack

    response = await _request(app, "POST", "/api/v1/standalone-events")

    assert response.status_code == 200
    assert await _rows(owner, world.table) == 1
    async with owner.connect() as conn:
        rows = list(
            (
                await conn.execute(
                    text("SELECT district_id FROM audit_logs WHERE user_sub = :s"), {"s": world.sub}
                )
            ).mappings()
        )
    async with owner.begin() as conn:
        await conn.execute(text("DELETE FROM audit_logs WHERE user_sub = :s"), {"s": world.sub})
    assert [r["district_id"] for r in rows] == [None]
