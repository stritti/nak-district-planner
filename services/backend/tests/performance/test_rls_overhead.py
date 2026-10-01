"""RLS overhead and tenant validation latency (OpenSpec improve-tenant-isolation).

Compares the matrix's hot queries as table owner (RLS bypassed) and as the
NOBYPASSRLS application role, in a database holding several districts.
Skipped unless configured:

    RLS_TEST_DATABASE_URL   owner DSN (superuser in CI, bypasses RLS)
    RLS_TEST_APP_PASSWORD   password of the application role
    APP_DB_USER             application role name (default: nak_app)

Measured values are documented in docs/security/tenant-isolation.md.
"""

from __future__ import annotations

import os
import statistics
import time as clock
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.application.tenant_validation import TenantValidationService

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

DISTRICTS = 5
CONGREGATIONS_PER_DISTRICT = 50
RANGE_FROM = date(2027, 1, 1)
RANGE_TO = date(2027, 3, 31)
RUNS = 30
# Regression guards against order-of-magnitude regressions such as per-row,
# unhashed membership subqueries or a missing index (migration 0024: the
# assignment lookup took ~240 ms as a full scan). Measured values are far lower
# and documented; client-side timings vary between runs, so the guards leave
# headroom for shared CI runners.
SLOT_QUERY_P95_BUDGET_MS = 250
ASSIGNMENT_QUERY_P95_BUDGET_MS = 100
VALIDATION_P95_BUDGET_MS = 25

_SLOTS = (
    "SELECT * FROM planning_slots WHERE district_id = :d "
    "AND planning_date BETWEEN :from_date AND :to_date"
)
_ASSIGNMENTS = "SELECT * FROM service_assignments WHERE planning_slot_id = ANY(:slot_ids)"


def _async_url(**overrides):
    return make_url(OWNER_DSN).set(drivername="postgresql+asyncpg", **overrides)


def _service_dates() -> list[date]:
    days = (RANGE_TO - RANGE_FROM).days + 1
    return [d for d in (RANGE_FROM + timedelta(n) for n in range(days)) if d.weekday() in (2, 6)]


@dataclass(frozen=True)
class Seeded:
    districts: list[uuid.UUID]
    planner_sub: str

    @property
    def measured(self) -> uuid.UUID:
        return self.districts[0]


@pytest.fixture
async def owner() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_async_url())
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_async_url(username=APP_ROLE, password=APP_PASSWORD))
    yield engine
    await engine.dispose()


@pytest.fixture
async def seeded(owner: AsyncEngine) -> AsyncIterator[Seeded]:
    data = Seeded([uuid.uuid4() for _ in range(DISTRICTS)], f"rls-perf-{uuid.uuid4().hex[:8]}")
    async with owner.begin() as conn:
        for district in data.districts:
            await conn.execute(
                text(
                    "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, 'Perf', now(), now())"
                ),
                {"id": district},
            )
            slots = []
            for _ in range(CONGREGATIONS_PER_DISTRICT):
                congregation = uuid.uuid4()
                await conn.execute(
                    text(
                        "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                        "VALUES (:id, 'Gemeinde', :d, now(), now())"
                    ),
                    {"id": congregation, "d": district},
                )
                slots += [
                    {"id": uuid.uuid4(), "d": district, "c": congregation, "day": day}
                    for day in _service_dates()
                ]
            await conn.execute(
                text(
                    "INSERT INTO planning_slots (id, district_id, congregation_id, category, "
                    "planning_date, planning_time, status, applicability, created_at, updated_at) "
                    "VALUES (:id, :d, :c, 'Gottesdienst', :day, '09:30', 'ACTIVE', '{}', now(), now())"
                ),
                slots,
            )
            await conn.execute(
                text(
                    "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_name, "
                    "status, created_at, updated_at) "
                    "VALUES (:id, :slot, :slot, 'Leiter', 'ASSIGNED', now(), now())"
                ),
                [{"id": uuid.uuid4(), "slot": slot["id"]} for slot in slots[::2]],
            )
        await conn.execute(
            text(
                "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
                "VALUES (:id, :sub, :sub, :sub, false, now(), now())"
            ),
            {"id": uuid.uuid4(), "sub": data.planner_sub},
        )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, "
                "updated_at) VALUES (:id, :sub, 'PLANNER', 'DISTRICT', :d, now(), now())"
            ),
            {"id": uuid.uuid4(), "sub": data.planner_sub, "d": data.measured},
        )
    async with owner.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(
            text("ANALYZE planning_slots, service_assignments, congregations, memberships, users")
        )
    yield data
    async with owner.begin() as conn:
        params = {"ids": data.districts, "sub": data.planner_sub}
        for statement in (
            "DELETE FROM service_assignments WHERE planning_slot_id IN "
            "(SELECT id FROM planning_slots WHERE district_id = ANY(:ids))",
            "DELETE FROM planning_slots WHERE district_id = ANY(:ids)",
            "DELETE FROM congregations WHERE district_id = ANY(:ids)",
            "DELETE FROM memberships WHERE user_sub = :sub",
            "DELETE FROM users WHERE sub = :sub",
            "DELETE FROM districts WHERE id = ANY(:ids)",
        ):
            await conn.execute(text(statement), params)


async def _measure(conn: AsyncConnection, sql: str, params: dict) -> tuple[list[float], int]:
    await conn.execute(text(sql), params)  # warm-up
    durations, rows = [], 0
    for _ in range(RUNS):
        started = clock.perf_counter()
        rows = len((await conn.execute(text(sql), params)).all())
        durations.append((clock.perf_counter() - started) * 1000)
    return durations, rows


def _p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=20)[-1]


async def _as_planner(engine: AsyncEngine, sub: str):
    conn = await engine.connect()
    await conn.execute(text("SELECT set_config('app.current_user_sub', :sub, false)"), {"sub": sub})
    return conn


async def test_rls_overhead_of_matrix_queries(owner, app_engine, seeded) -> None:
    slot_params = {"d": seeded.measured, "from_date": RANGE_FROM, "to_date": RANGE_TO}
    async with owner.connect() as conn:
        bypass_slots, expected_slots = await _measure(conn, _SLOTS, slot_params)
        slot_ids = [row.id for row in (await conn.execute(text(_SLOTS), slot_params)).all()]
        bypass_assignments, expected_assignments = await _measure(
            conn, _ASSIGNMENTS, {"slot_ids": slot_ids}
        )

    conn = await _as_planner(app_engine, seeded.planner_sub)
    try:
        rls_slots, slots = await _measure(conn, _SLOTS, slot_params)
        rls_assignments, assignments = await _measure(conn, _ASSIGNMENTS, {"slot_ids": slot_ids})
    finally:
        await conn.close()

    # Same result as without RLS: the planner sees the whole own district.
    assert (slots, assignments) == (expected_slots, expected_assignments)
    print(
        f"\nslots ({slots}): bypass p95={_p95(bypass_slots):.1f} ms, rls p95={_p95(rls_slots):.1f} ms"
        f"\nassignments ({assignments}): bypass p95={_p95(bypass_assignments):.1f} ms, "
        f"rls p95={_p95(rls_assignments):.1f} ms"
    )
    assert _p95(rls_slots) <= SLOT_QUERY_P95_BUDGET_MS
    assert _p95(rls_assignments) <= ASSIGNMENT_QUERY_P95_BUDGET_MS


async def test_rls_hides_other_districts_at_scale(app_engine, seeded) -> None:
    conn = await _as_planner(app_engine, seeded.planner_sub)
    try:
        foreign = await conn.execute(
            text("SELECT count(*) FROM planning_slots WHERE district_id = ANY(:ids)"),
            {"ids": seeded.districts[1:]},
        )
        assert foreign.scalar_one() == 0
    finally:
        await conn.close()


async def test_tenant_validation_latency(app_engine, seeded) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(app_engine) as session:
        await session.execute(
            text("SELECT set_config('app.current_user_sub', :sub, false)"),
            {"sub": seeded.planner_sub},
        )
        service = TenantValidationService(session)
        await service.validate_user_in_district(seeded.planner_sub, seeded.measured)  # warm-up
        durations = []
        for _ in range(RUNS):
            started = clock.perf_counter()
            await service.validate_user_in_district(seeded.planner_sub, seeded.measured)
            durations.append((clock.perf_counter() - started) * 1000)

    print(f"\ntenant validation p95={_p95(durations):.2f} ms")
    assert _p95(durations) <= VALIDATION_P95_BUDGET_MS
