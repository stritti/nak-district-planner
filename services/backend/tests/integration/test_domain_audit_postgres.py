"""Domain audit hook against a real, migrated PostgreSQL with active RLS.

The audited writes run as the NOBYPASSRLS application role with the same GUCs
the application sets, so the tests prove that every actor allowed to change an
audited row can also write its audit entry. Skipped unless configured:

    RLS_TEST_DATABASE_URL   owner DSN used to seed and inspect fixtures,
                            e.g. postgresql://nak:changeme@localhost:5432/nak_rls
    RLS_TEST_APP_PASSWORD   password of the application role
    APP_DB_USER             application role name (default: nak_app)
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.adapters.db.orm_models.calendar_integration import CalendarIntegrationORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.adapters.db.session import AuditedSession, _set_tenant_gucs
from app.domain.models.planning_slot import PlanningSlotStatus
from app.domain.models.service_assignment import AssignmentStatus
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
class Seed:
    run: str
    district_id: uuid.UUID
    congregation_id: uuid.UUID
    congregation_slot_id: uuid.UUID
    integration_id: uuid.UUID

    def sub(self, name: str) -> str:
        return f"audit-{self.run}-{name}"


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
async def seed(owner: AsyncEngine) -> AsyncIterator[Seed]:
    s = Seed(uuid.uuid4().hex[:8], uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    members = [
        ("planner", "PLANNER", "DISTRICT", s.district_id),
        ("gemeinde", "CONGREGATION_ADMIN", "CONGREGATION", s.congregation_id),
    ]
    async with owner.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, :n, now(), now())"
            ),
            {"id": s.district_id, "n": f"Audit {s.run}"},
        )
        await conn.execute(
            text(
                "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                "VALUES (:id, 'Gemeinde', :d, now(), now())"
            ),
            {"id": s.congregation_id, "d": s.district_id},
        )
        await conn.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, congregation_id, planning_date, "
                "planning_time, status, created_at, updated_at) "
                "VALUES (:id, :d, :c, '2026-12-24', '18:00', 'ACTIVE', now(), now())"
            ),
            {"id": s.congregation_slot_id, "d": s.district_id, "c": s.congregation_id},
        )
        await conn.execute(
            text(
                "INSERT INTO calendar_integrations (id, district_id, name, type, credentials_enc, "
                "created_at, updated_at, delete_behavior) "
                "VALUES (:id, :d, 'Feed', 'ICS', 'cipher-old', now(), now(), 'MARK_CANCELLED')"
            ),
            {"id": s.integration_id, "d": s.district_id},
        )
        for name, role, scope_type, scope_id in members:
            await conn.execute(
                text(
                    "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
                    "VALUES (:id, :sub, :email, :sub, false, now(), now())"
                ),
                {"id": uuid.uuid4(), "sub": s.sub(name), "email": f"{s.sub(name)}@example.org"},
            )
            await conn.execute(
                text(
                    "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, "
                    "updated_at) VALUES (:id, :sub, :role, :scope_type, :scope_id, now(), now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "sub": s.sub(name),
                    "role": role,
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                },
            )
    yield s
    async with owner.begin() as conn:
        await conn.execute(
            text("DELETE FROM audit_logs WHERE district_id = :d"), {"d": s.district_id}
        )
        await conn.execute(
            text("DELETE FROM memberships WHERE user_sub LIKE :p"), {"p": f"audit-{s.run}-%"}
        )
        await conn.execute(text("DELETE FROM users WHERE sub LIKE :p"), {"p": f"audit-{s.run}-%"})
        for table in ("calendar_integrations", "planning_slots", "congregations"):
            await conn.execute(
                text(f"DELETE FROM {table} WHERE district_id = :d"),  # noqa: S608
                {"d": s.district_id},
            )
        await conn.execute(text("DELETE FROM districts WHERE id = :d"), {"d": s.district_id})


@asynccontextmanager
async def acting_as(engine: AsyncEngine, user_sub: str, roles: list[str]):
    TenantContext.set_context(user_sub=user_sub, user_roles=roles)
    factory = async_sessionmaker(engine, expire_on_commit=False, sync_session_class=AuditedSession)
    try:
        async with factory() as session:
            yield session
    finally:
        TenantContext.clear_context()


async def _audit_rows(owner: AsyncEngine, resource_id: uuid.UUID) -> list:
    async with owner.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT action, user_sub, district_id, congregation_id, old_values, new_values, "
                "changes, extra_metadata FROM audit_logs WHERE resource_id = :id ORDER BY timestamp"
            ),
            {"id": resource_id},
        )
        return list(result.mappings())


def _new_slot(seed: Seed) -> PlanningSlotORM:
    now = datetime.now(UTC)
    return PlanningSlotORM(
        id=uuid.uuid4(),
        district_id=seed.district_id,
        title="Gottesdienst",
        planning_date=date(2026, 12, 25),
        planning_time=time(9, 30),
        status=PlanningSlotStatus.ACTIVE,
        applicability=[],
        created_at=now,
        updated_at=now,
    )


async def test_create_and_update_are_audited_with_actor_and_diff(owner, app_engine, seed) -> None:
    slot = _new_slot(seed)
    async with acting_as(app_engine, seed.sub("planner"), ["PLANNER"]) as session:
        session.add(slot)
        await session.commit()
        slot.title = "Festgottesdienst"
        await session.commit()

    created, updated = await _audit_rows(owner, slot.id)
    assert created["action"] == "CREATE"
    assert created["user_sub"] == seed.sub("planner")
    assert created["district_id"] == seed.district_id
    assert created["new_values"]["title"] == "Gottesdienst"
    assert created["extra_metadata"] == {"source": "domain"}
    assert updated["action"] == "UPDATE"
    assert (updated["old_values"], updated["new_values"]) == (
        {"title": "Gottesdienst"},
        {"title": "Festgottesdienst"},
    )


async def test_rolled_back_change_leaves_no_audit_entry(owner, app_engine, seed) -> None:
    slot = _new_slot(seed)
    async with acting_as(app_engine, seed.sub("planner"), ["PLANNER"]) as session:
        session.add(slot)
        await session.flush()
        await session.rollback()

    assert await _audit_rows(owner, slot.id) == []


async def test_congregation_member_can_audit_assignment_on_own_slot(
    owner, app_engine, seed
) -> None:
    now = datetime.now(UTC)
    assignment = ServiceAssignmentORM(
        id=uuid.uuid4(),
        event_id=seed.congregation_slot_id,
        planning_slot_id=seed.congregation_slot_id,
        leader_name="Anna Beispiel",
        status=AssignmentStatus.ASSIGNED,
        created_at=now,
        updated_at=now,
    )
    async with acting_as(app_engine, seed.sub("gemeinde"), ["CONGREGATION_ADMIN"]) as session:
        session.add(assignment)
        await session.commit()
        await session.delete(assignment)
        await session.commit()

    rows = await _audit_rows(owner, assignment.id)
    assert [row["action"] for row in rows] == ["CREATE", "DELETE"]
    assert {(row["district_id"], row["congregation_id"]) for row in rows} == {
        (seed.district_id, seed.congregation_id)
    }


async def test_system_worker_credential_rotation_is_audited_without_secrets(
    owner, app_engine, seed
) -> None:
    async with acting_as(app_engine, "system:celery-worker", ["SYSTEM_WORKER"]) as session:
        integration = await session.get(CalendarIntegrationORM, seed.integration_id)
        integration.credentials_enc = "cipher-new"
        integration.last_synced_at = datetime.now(UTC)
        await session.commit()

    [row] = await _audit_rows(owner, seed.integration_id)
    assert row["action"] == "UPDATE"
    assert row["user_sub"] == "system:celery-worker"
    assert row["changes"] == {"redacted_fields": ["credentials_enc"]}
    assert "cipher" not in str(dict(row))
