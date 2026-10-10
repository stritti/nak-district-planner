# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Performance baseline (OpenSpec introduce-non-functional-baseline, tasks 3.1/3.2).

Runs against a real, migrated PostgreSQL as the NOBYPASSRLS application role,
so RLS overhead is part of every measurement. Skipped unless configured:

    RLS_TEST_DATABASE_URL   owner DSN used to seed fixtures
    RLS_TEST_APP_PASSWORD   password of the application role
    APP_DB_USER             application role name (default: nak_app)

Budgets are the spec thresholds; measured values are documented in
docs/performance-baseline.md.
"""

from __future__ import annotations

import os
import statistics
import time as clock
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.adapters.api import deps
from app.adapters.db.session import AuditedSession, _set_tenant_gucs, get_db_session
from app.application import sync_service
from app.application.crypto import encrypt_credentials
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.models.role import Role
from app.domain.models.user import User
from app.domain.ports.calendar import CalendarConnector
from app.tenant import TenantContext

OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = pytest.mark.skipif(
    not (OWNER_DSN and APP_PASSWORD),
    reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
)

# District-scale load from the spec: 50 congregations, a 3-month range.
CONGREGATIONS = 50
LEADERS = 100
RANGE_FROM = date(2027, 1, 1)
RANGE_TO = date(2027, 3, 31)
MATRIX_P95_BUDGET_MS = 500
MATRIX_RUNS = 15

SYNC_EVENTS = 500
# Regression guards at roughly twice the measured local values, leaving headroom
# for shared CI runners. The resync of an unchanged feed is barely faster than
# the initial import because every event is looked up individually (N+1); see
# docs/performance-baseline.md.
SYNC_INITIAL_BUDGET_S = 12.0
SYNC_UNCHANGED_BUDGET_S = 10.0


def _async_url(**overrides):
    return make_url(OWNER_DSN).set(drivername="postgresql+asyncpg", **overrides)


def _service_dates(start: date, end: date) -> list[date]:
    """Sundays and Wednesdays, the default congregation service schedule."""
    days = (end - start).days + 1
    return [d for d in (start + timedelta(n) for n in range(days)) if d.weekday() in (2, 6)]


@dataclass(frozen=True)
class District:
    id: uuid.UUID
    viewer_sub: str
    integration_id: uuid.UUID


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


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


async def _seed(conn, district_id: uuid.UUID, viewer_sub: str, integration_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await conn.execute(
        text(
            "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, 'Perf', :now, :now)"
        ),
        {"id": district_id, "now": now},
    )
    congregations = [uuid.uuid4() for _ in range(CONGREGATIONS)]
    await conn.execute(
        text(
            "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
            "VALUES (:id, :name, :d, :now, :now)"
        ),
        [
            {"id": c, "name": f"Gemeinde {i:02}", "d": district_id, "now": now}
            for i, c in enumerate(congregations)
        ],
    )
    leaders = [uuid.uuid4() for _ in range(LEADERS)]
    await conn.execute(
        text("INSERT INTO leaders (id, name, district_id) VALUES (:id, :name, :d)"),
        [
            {"id": leader, "name": f"Leiter {i}", "d": district_id}
            for i, leader in enumerate(leaders)
        ],
    )
    slots, assignments = [], []
    for c_index, congregation in enumerate(congregations):
        for d_index, day in enumerate(_service_dates(RANGE_FROM, RANGE_TO)):
            slot_id = uuid.uuid4()
            slots.append(
                {
                    "id": slot_id,
                    "d": district_id,
                    "c": congregation,
                    "day": day,
                    "t": time(9, 30) if day.weekday() == 6 else time(20),
                    "now": now,
                }
            )
            if (c_index + d_index) % 3:  # two thirds assigned, one third are gaps
                assignments.append(
                    {
                        "id": uuid.uuid4(),
                        "slot": slot_id,
                        "leader": leaders[d_index % LEADERS],
                        "now": now,
                    }
                )
    await conn.execute(
        text(
            "INSERT INTO planning_slots (id, district_id, congregation_id, category, title, "
            "planning_date, planning_time, status, applicability, created_at, updated_at) "
            "VALUES (:id, :d, :c, 'Gottesdienst', 'Gottesdienst', :day, :t, 'ACTIVE', '{}', :now, :now)"
        ),
        slots,
    )
    await conn.execute(
        text(
            "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_id, status, "
            "created_at, updated_at) VALUES (:id, :slot, :slot, :leader, 'ASSIGNED', :now, :now)"
        ),
        assignments,
    )
    await conn.execute(
        text(
            "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
            "VALUES (:id, :sub, :email, :sub, false, :now, :now)"
        ),
        {"id": uuid.uuid4(), "sub": viewer_sub, "email": f"{viewer_sub}@example.org", "now": now},
    )
    await conn.execute(
        text(
            "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, "
            "updated_at) VALUES (:id, :sub, 'VIEWER', 'DISTRICT', :d, :now, :now)"
        ),
        {"id": uuid.uuid4(), "sub": viewer_sub, "d": district_id, "now": now},
    )
    await conn.execute(
        text(
            "INSERT INTO calendar_integrations (id, district_id, name, type, credentials_enc, "
            "created_at, updated_at, delete_behavior) "
            "VALUES (:id, :d, 'Perf-Feed', 'ICS', :cred, :now, :now, 'MARK_CANCELLED')"
        ),
        {
            "id": integration_id,
            "d": district_id,
            "now": now,
            "cred": encrypt_credentials({"url": "https://calendar.invalid/feed.ics"}),
        },
    )


_ANALYZED_TABLES = (
    "congregations",
    "leaders",
    "planning_slots",
    "service_assignments",
    "memberships",
    "users",
    "calendar_integrations",
)

_CLEANUP = (
    "DELETE FROM audit_logs WHERE district_id = :d",
    "DELETE FROM external_event_links WHERE calendar_integration_id = :i",
    "DELETE FROM external_event_candidates WHERE calendar_integration_id = :i",
    "DELETE FROM notifications WHERE district_id = :d",
    "DELETE FROM service_assignments WHERE planning_slot_id IN "
    "(SELECT id FROM planning_slots WHERE district_id = :d)",
    "DELETE FROM event_instances WHERE planning_slot_id IN "
    "(SELECT id FROM planning_slots WHERE district_id = :d)",
    "DELETE FROM planning_slots WHERE district_id = :d",
    "DELETE FROM calendar_integrations WHERE district_id = :d",
    "DELETE FROM leaders WHERE district_id = :d",
    "DELETE FROM congregations WHERE district_id = :d",
    "DELETE FROM memberships WHERE user_sub = :sub",
    "DELETE FROM users WHERE sub = :sub",
    "DELETE FROM districts WHERE id = :d",
)


@pytest.fixture
async def district(owner: AsyncEngine) -> AsyncIterator[District]:
    seeded = District(uuid.uuid4(), f"perf-{uuid.uuid4().hex[:8]}", uuid.uuid4())
    async with owner.begin() as conn:
        await _seed(conn, seeded.id, seeded.viewer_sub, seeded.integration_id)
    # Production tables are analysed by autovacuum; right after a bulk seed the
    # planner would estimate single rows and pick plans that depend on timing.
    async with owner.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text(f"ANALYZE {', '.join(_ANALYZED_TABLES)}"))
    yield seeded
    async with owner.begin() as conn:
        for statement in _CLEANUP:
            await conn.execute(
                text(statement),
                {"d": seeded.id, "i": seeded.integration_id, "sub": seeded.viewer_sub},
            )


async def _durations_ms(run: Callable[[], Awaitable[Any]], repetitions: int) -> list[float]:
    durations = []
    for _ in range(repetitions):
        started = clock.perf_counter()
        await run()
        durations.append((clock.perf_counter() - started) * 1000)
    return durations


def _p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=20)[-1]


async def test_matrix_endpoint_meets_latency_budget(app_engine, district) -> None:
    from app.main import app

    factory = async_sessionmaker(
        app_engine, expire_on_commit=False, sync_session_class=AuditedSession
    )
    viewer = deps.CurrentUserContext(
        user=User(sub=district.viewer_sub, email="viewer@example.org", username="viewer"),
        memberships=[
            Membership.create(
                user_sub=district.viewer_sub,
                role=Role.VIEWER,
                scope_type=ScopeType.DISTRICT,
                scope_id=district.id,
            )
        ],
    )

    async def db_session():
        # Same GUCs as production: the begin-listener reads the tenant context.
        TenantContext.set_context(user_sub=district.viewer_sub, user_roles=["VIEWER"])
        try:
            async with factory() as session:
                yield session
        finally:
            TenantContext.clear_context()

    app.dependency_overrides[deps.require_membership_access] = lambda: viewer
    app.dependency_overrides[get_db_session] = db_session
    params = {"from_dt": f"{RANGE_FROM}T00:00:00Z", "to_dt": f"{RANGE_TO}T23:59:59Z"}
    url = f"/api/v1/districts/{district.id}/matrix"
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            async def request() -> None:
                response = await client.get(url, params=params)
                assert response.status_code == 200, response.text

            response = await client.get(url, params=params)  # warm-up, checked for content
            body = response.json()
            durations = await _durations_ms(request, MATRIX_RUNS)
    finally:
        app.dependency_overrides.clear()

    assert len(body["rows"]) == CONGREGATIONS
    assert len(body["dates"]) == len(_service_dates(RANGE_FROM, RANGE_TO))
    gaps = sum(cell["is_gap"] for row in body["rows"] for cell in row["cells"].values())
    assert gaps == pytest.approx(CONGREGATIONS * len(body["dates"]) / 3, rel=0.05)
    p95 = _p95(durations)
    print(f"\nmatrix p50={statistics.median(durations):.0f} ms p95={p95:.0f} ms")
    assert p95 <= MATRIX_P95_BUDGET_MS


class _StaticFeed(CalendarConnector):
    def __init__(self, events: list[RawCalendarEvent]) -> None:
        self._events = events

    async def fetch_events(self, credentials, from_dt=None, to_dt=None):
        return self._events


def _feed(count: int) -> list[RawCalendarEvent]:
    start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    events = []
    for n in range(count):
        begins = start + timedelta(hours=6 * n)
        events.append(
            RawCalendarEvent(
                uid=f"perf-{n}@example.org",
                title=f"Termin {n}",
                start_at=begins,
                end_at=begins + timedelta(hours=1),
                description=None,
                content_hash="",
                is_cancelled=False,
            )
        )
    return events


async def _candidate_count(owner: AsyncEngine, integration_id: uuid.UUID) -> int:
    async with owner.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT count(*) FROM external_event_candidates WHERE calendar_integration_id = :i"
            ),
            {"i": integration_id},
        )
        return result.scalar_one()


async def test_sync_duration_for_district_feed(owner, app_engine, district) -> None:
    feed = _StaticFeed(_feed(SYNC_EVENTS))
    factory = async_sessionmaker(
        app_engine, expire_on_commit=False, sync_session_class=AuditedSession
    )

    async def sync() -> sync_service.SyncResult:
        TenantContext.set_context(user_sub="system:celery-worker", user_roles=["SYSTEM_WORKER"])
        try:
            async with factory() as session:
                result = await sync_service.run_sync(district.integration_id, session)
                await session.commit()
                return result
        finally:
            TenantContext.clear_context()

    with patch.object(sync_service, "_get_connector", return_value=feed):
        started = clock.perf_counter()
        initial = await sync()
        initial_s = clock.perf_counter() - started
        started = clock.perf_counter()
        unchanged = await sync()
        unchanged_s = clock.perf_counter() - started

    print(f"\nsync {SYNC_EVENTS} events: initial={initial_s:.2f} s unchanged={unchanged_s:.2f} s")
    # Unknown external events become review candidates (governance since #376);
    # the resync must recognise all of them instead of creating duplicates.
    assert (initial.skipped, initial.failed) == (SYNC_EVENTS, 0)
    assert (unchanged.created, unchanged.updated, unchanged.failed) == (0, 0, 0)
    assert await _candidate_count(owner, district.integration_id) == SYNC_EVENTS
    assert initial_s <= SYNC_INITIAL_BUDGET_S
    assert unchanged_s <= SYNC_UNCHANGED_BUDGET_S
