"""Repeatable PostgreSQL query-plan evidence for event listing (#626).

Seeds through the owner DSN and measures through the NOBYPASSRLS application role,
so plans include the RLS predicates production applies. Never uses production data.
No wall-clock thresholds: CI runners have variable performance characteristics.

    TEST_DATABASE_URL       owner DSN (superuser in CI)
    RLS_TEST_APP_PASSWORD   password of the application role
    APP_DB_USER             application role name (default: nak_app)
"""

from __future__ import annotations

import json
import os
import statistics
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import event, make_url, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository

OWNER_DSN = os.getenv("TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = pytest.mark.skipif(
    not (OWNER_DSN and APP_PASSWORD),
    reason="TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
)

PLAN_REPORT = Path(__file__).resolve().parents[2] / "event-list-query-plans.json"
START, END = date(2031, 1, 1), date(2031, 12, 31)
SIZE = 50_000
DISTRICT_DATE_INDEX = "ix_planning_slots_district_date"
SAMPLES = 5  # measured EXPLAIN ANALYZE runs per statement, after one warm-up
# Bounds every query of the measured path, including the warm-up list_page() call.
_TIMEOUT = {"server_settings": {"statement_timeout": "10s"}}


@pytest.fixture
async def workload():
    """Seed 50k own-tenant slots and 1k other-tenant slots for a district planner."""
    owner = create_async_engine(OWNER_DSN, pool_pre_ping=True)
    app = create_async_engine(
        make_url(OWNER_DSN).set(username=APP_ROLE, password=APP_PASSWORD), connect_args=_TIMEOUT
    )
    district, foreign = uuid.uuid4(), uuid.uuid4()
    congregations = [uuid.uuid4() for _ in range(25)]
    planner = f"perf-planner-{district.hex[:8]}"
    try:
        async with owner.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO districts (id, name, created_at, updated_at) "
                    "VALUES (:id, :name, now(), now())"
                ),
                [
                    {"id": district, "name": f"Perf district {district.hex}"},
                    {"id": foreign, "name": f"Perf foreign {foreign.hex}"},
                ],
            )
            await connection.execute(
                text(
                    "INSERT INTO congregations "
                    "(id, name, district_id, created_at, updated_at) "
                    "VALUES (:id, :name, :district, now(), now())"
                ),
                [
                    {"id": cong, "name": f"Perf G {i} {district.hex}", "district": district}
                    for i, cong in enumerate(congregations)
                ],
            )
            await connection.execute(
                text(
                    """
                    WITH numbered AS (
                      SELECT id, row_number() OVER (ORDER BY id) AS rn
                      FROM congregations WHERE district_id=:district
                    )
                    INSERT INTO planning_slots (
                      id, district_id, congregation_id, category,
                      planning_date, planning_time, status, approval_status,
                      applicability, created_at, updated_at
                    )
                    SELECT gen_random_uuid(), :district,
                      CASE WHEN gs.i % 4 = 0 THEN NULL ELSE numbered.id END,
                      CASE WHEN gs.i % 3 = 0 THEN 'Gottesdienst' ELSE 'Probe' END,
                      DATE '2031-01-01' + (gs.i % 365),
                      TIME '06:00' + ((gs.i / 1825) * INTERVAL '30 minutes'),
                      CAST('ACTIVE' AS planning_slot_status),
                      CAST('CONFIRMED' AS event_approval_status),
                      CASE WHEN gs.i % 4 = 0 THEN ARRAY['all']::text[] ELSE ARRAY[]::text[] END,
                      now(), now()
                    FROM generate_series(1, :size) AS gs(i)
                    JOIN numbered ON numbered.rn = 1 + (gs.i % 25)
                    """
                ),
                {"district": district, "size": SIZE},
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO planning_slots (
                      id, district_id, category, planning_date, planning_time,
                      status, applicability, created_at, updated_at
                    )
                    SELECT gen_random_uuid(), :district, 'Gottesdienst',
                      DATE '2031-01-01' + (gs % 365), TIME '09:00',
                      CAST('ACTIVE' AS planning_slot_status),
                      ARRAY[]::text[], now(), now()
                    FROM generate_series(1, 1000) AS gs
                    """
                ),
                {"district": foreign},
            )
            await connection.execute(
                text(
                    "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, "
                    "updated_at) VALUES (:id, :sub, :sub, :sub, false, now(), now())"
                ),
                {"id": uuid.uuid4(), "sub": planner},
            )
            await connection.execute(
                text(
                    "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, "
                    "created_at, updated_at) "
                    "VALUES (:id, :sub, 'PLANNER', 'DISTRICT', :d, now(), now())"
                ),
                {"id": uuid.uuid4(), "sub": planner, "d": district},
            )
        await _maintain(owner, "ANALYZE")  # plan from current statistics, not empty ones
        yield app, planner, district, congregations
    finally:
        async with owner.begin() as connection:
            await connection.execute(
                text("DELETE FROM planning_slots WHERE district_id IN (:own, :foreign)"),
                {"own": district, "foreign": foreign},
            )
            await connection.execute(
                text("DELETE FROM memberships WHERE user_sub=:sub"), {"sub": planner}
            )
            await connection.execute(text("DELETE FROM users WHERE sub=:sub"), {"sub": planner})
            await connection.execute(
                text("DELETE FROM congregations WHERE district_id=:own"), {"own": district}
            )
            await connection.execute(
                text("DELETE FROM districts WHERE id IN (:own, :foreign)"),
                {"own": district, "foreign": foreign},
            )
        # Reclaim the deleted rows so later performance tests see an unbloated table.
        await _maintain(owner, "VACUUM ANALYZE")
        await owner.dispose()
        await app.dispose()


async def _maintain(engine, command: str) -> None:
    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(text(f"{command} planning_slots, memberships"))


async def _as_planner(engine, planner: str):
    connection = await engine.connect()
    await connection.execute(
        text("SELECT set_config('app.current_user_sub', :sub, false)"), {"sub": planner}
    )
    return connection


async def _query_with_plans(engine, planner, **filters) -> tuple[int, list[dict]]:
    """EXPLAIN exactly the SQL/DBAPI parameters list_page() sends as the planner."""
    captured: list[tuple[str, object]] = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "planning_slots" in statement:
            captured.append((statement, parameters))

    connection = await _as_planner(engine, planner)
    try:
        event.listen(engine.sync_engine, "before_cursor_execute", capture)
        try:
            session = async_sessionmaker(bind=connection, expire_on_commit=False)()
            async with session:
                page, total = await SqlPlanningSlotRepository(session).list_page(**filters)
                assert len(page) <= filters["limit"]
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", capture)

        assert len(captured) == 2, "Expected independent COUNT and page SQL queries"
        evidence = []
        for query, params in captured:
            samples = []
            for _ in range(SAMPLES):
                plan = (
                    await connection.exec_driver_sql(
                        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query, params
                    )
                ).scalar_one()
                samples.append((json.loads(plan) if isinstance(plan, str) else plan)[0])
            times = [sample["Execution Time"] for sample in samples]
            evidence.append(
                {"median_ms": statistics.median(times), "max_ms": max(times)} | samples[-1]
            )
    finally:
        await connection.close()
    return total, evidence


def _indexes(node: dict) -> set[str]:
    """Index names used anywhere in an EXPLAIN JSON plan node."""
    names = {node["Index Name"]} if "Index Name" in node else set()
    for child in node.get("Plans", []):
        names |= _indexes(child)
    return names


async def test_event_listing_50k_query_plans(workload) -> None:
    engine, planner, district, congregations = workload
    base = {
        "district_id": district,
        "from_date": START,
        "to_date": END,
        "limit": 500,
        "offset": 0,
    }
    reports = {}
    for name, options in {
        "district_first": {},
        "district_deep": {"offset": 10_000},
        "congregation": {"congregation_id": congregations[0]},
        "district_only": {"only_district_level": True},
    }.items():
        total, plans = await _query_with_plans(engine, planner, **(base | options))
        assert 0 < total <= SIZE
        assert all("Plan" in entry and "Execution Time" in entry for entry in plans)
        reports[name] = {
            "total": total,
            "count_median_ms": plans[0]["median_ms"],
            "page_median_ms": plans[1]["median_ms"],
            "plans": plans,
        }
    PLAN_REPORT.write_text(json.dumps(reports, indent=2, default=str), encoding="utf-8")
    # Every page query reads the slots through the district/date index (no sequential scan).
    for name, report in reports.items():
        assert DISTRICT_DATE_INDEX in _indexes(report["plans"][1]["Plan"]), name
    # Exact totals of the deterministic fixture: the reference semantics hold and none of
    # the foreign district's slots leak in. Every 4th slot is a district event
    # (applicability ``all``); a congregation sees its own 1/25 of the rest plus those.
    assert reports["district_first"]["total"] == SIZE
    assert reports["district_deep"]["total"] == SIZE
    assert reports["district_only"]["total"] == SIZE // 4
    assert reports["congregation"]["total"] == 14_000
