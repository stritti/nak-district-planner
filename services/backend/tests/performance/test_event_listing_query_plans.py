# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Repeatable PostgreSQL query-plan evidence for event listing (#626).

Runs only with a real migrated TEST_DATABASE_URL; never uses production data.
No wall-clock thresholds: CI runners have variable performance characteristics.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)

PLAN_REPORT = Path(__file__).resolve().parents[2] / "event-list-query-plans.json"
START, END = date(2031, 1, 1), date(2031, 12, 31)
SIZE = 50_000


@pytest.fixture
async def workload():
    """Seed 50k own-tenant slots and 1k other-tenant slots, then remove both."""
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    district, foreign = uuid.uuid4(), uuid.uuid4()
    congregations = [uuid.uuid4() for _ in range(25)]
    try:
        async with engine.begin() as connection:
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
                      DATE '2031-01-01' + (gs.i % 365), TIME '09:00',
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
        yield sessions, engine, district, congregations
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM planning_slots WHERE district_id IN (:own, :foreign)"),
                {"own": district, "foreign": foreign},
            )
            await connection.execute(
                text("DELETE FROM congregations WHERE district_id=:own"), {"own": district}
            )
            await connection.execute(
                text("DELETE FROM districts WHERE id IN (:own, :foreign)"),
                {"own": district, "foreign": foreign},
            )
        await engine.dispose()


async def _query_with_plans(engine, sessions, **filters) -> tuple[int, list[dict]]:
    """EXPLAIN exactly the SQL/DBAPI parameters used by list_page()."""
    captured: list[tuple[str, object]] = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "planning_slots" in statement:
            captured.append((statement, parameters))

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with sessions() as session:
            page, total = await SqlPlanningSlotRepository(session).list_page(**filters)
            assert len(page) <= filters["limit"]
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

    assert len(captured) == 2, "Expected independent COUNT and page SQL queries"
    evidence = []
    async with engine.connect() as connection:
        await connection.execute(text("SET statement_timeout TO '10s'"))
        for query, params in captured:
            row = (
                await connection.exec_driver_sql(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query, params
                )
            ).first()
            plan = row[0]
            if isinstance(plan, str):
                plan = json.loads(plan)
            evidence.append(plan[0])
    return total, evidence


async def test_event_listing_50k_query_plans(workload) -> None:
    sessions, engine, district, congregations = workload
    base = {
        "district_id": district, "from_date": START, "to_date": END,
        "limit": 500, "offset": 0,
    }
    reports = {}
    for name, options in {
        "district_first": {},
        "district_deep": {"offset": 10_000},
        "congregation": {"congregation_id": congregations[0]},
        "district_only": {"only_district_level": True},
    }.items():
        total, plans = await _query_with_plans(engine, sessions, **(base | options))
        assert 0 < total <= SIZE
        assert all("Plan" in entry and "Execution Time" in entry for entry in plans)
        reports[name] = {
            "total": total,
            "count_ms": plans[0]["Execution Time"],
            "page_ms": plans[1]["Execution Time"],
            "plans": plans,
        }
    assert reports["district_first"]["total"] == SIZE
    assert reports["district_deep"]["total"] == SIZE
    PLAN_REPORT.write_text(json.dumps(reports, indent=2, default=str), encoding="utf-8")
