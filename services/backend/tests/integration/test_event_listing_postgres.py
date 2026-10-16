# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQL-side event listing equals the former in-memory semantics (#604).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import itertools
import os
import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.api.routers.events import SERVICE_CATEGORY
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)

DAY = date(2031, 6, 1)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def tenant(sessions):
    ids = {k: uuid.uuid4() for k in ("district", "other", "c1", "c2", "c3")}
    now = datetime.now(UTC)
    slots: list[dict] = []
    variants = itertools.product(
        (None, "c1", "c2"),
        ("ACTIVE", "CANCELLED"),
        ("PLANNED", "CONFIRMED"),
        (SERVICE_CATEGORY, "Probe", None),
        ((), ("all",), ("c1",), ("c2", "c3")),
    )
    for i, (cong, status, approval, category, applicability) in enumerate(variants):
        slots.append(
            {
                "id": uuid.uuid4(),
                "day": DAY + timedelta(days=i % 9),
                "time": time(9 + i % 5, 0),
                "cong": ids[cong] if cong else None,
                "status": status,
                "approval": approval,
                "category": category,
                "applicability": ["all" if a == "all" else str(ids[a]) for a in applicability],
            }
        )
    async with sessions() as db, db.begin():
        for district in ("district", "other"):
            await db.execute(
                text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, 'B', :n, :n)"),
                {"i": ids[district], "n": now},
            )
        for cong in ("c1", "c2", "c3"):
            await db.execute(
                text(
                    "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
                    "VALUES (:i, 'G', :d, :n, :n)"
                ),
                {"i": ids[cong], "d": ids["district"], "n": now},
            )
        for slot in slots:
            await db.execute(
                text(
                    "INSERT INTO planning_slots (id, district_id, congregation_id, category, "
                    "planning_date, planning_time, status, approval_status, applicability, "
                    "created_at, updated_at) VALUES (:id, :d, :c, :cat, :day, :t, "
                    "CAST(:st AS planning_slot_status), CAST(:ap AS event_approval_status), :app, :n, :n)"
                ),
                {
                    "id": slot["id"], "d": ids["district"], "c": slot["cong"], "cat": slot["category"],
                    "day": slot["day"], "t": slot["time"], "st": slot["status"],
                    "ap": slot["approval"], "app": slot["applicability"], "n": now,
                },
            )
        # A slot of another district must never leak into the listing.
        await db.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, category, planning_date, planning_time, "
                "status, applicability, created_at, updated_at) VALUES (:id, :d, 'Gottesdienst', :day, "
                "'09:00', 'ACTIVE', '{}', :n, :n)"
            ),
            {"id": uuid.uuid4(), "d": ids["other"], "day": DAY, "n": now},
        )
    yield ids
    async with sessions() as db, db.begin():
        for district in ("district", "other"):
            await db.execute(text("DELETE FROM planning_slots WHERE district_id=:i"), {"i": ids[district]})
        await db.execute(text("DELETE FROM congregations WHERE district_id=:i"), {"i": ids["district"]})
        for district in ("district", "other"):
            await db.execute(text("DELETE FROM districts WHERE id=:i"), {"i": ids[district]})


def _reference(
    slots: list[PlanningSlot], *, congregation_id, group_ids, only_district, status, approval, is_service
) -> list[PlanningSlot]:
    """The former router logic, kept here as the behavioural oracle."""
    if group_ids is not None:
        slots = [s for s in slots if s.congregation_id is None or s.congregation_id in group_ids]
    if only_district:
        slots = [s for s in slots if s.congregation_id is None]
    elif congregation_id is not None:
        slots = [
            s
            for s in slots
            if s.congregation_id == congregation_id
            or (s.status == PlanningSlotStatus.ACTIVE and s.is_distributed_to(congregation_id))
        ]
    if status is not None:
        slots = [s for s in slots if s.status == status]
    if approval is not None:
        slots = [s for s in slots if s.approval_status == approval]
    if is_service is not None:
        slots = [s for s in slots if (s.category == SERVICE_CATEGORY) == is_service]
    return slots


FILTERS = [
    {},
    {"only_district": True},
    {"congregation": "c1"},
    {"congregation": "c2", "status": PlanningSlotStatus.ACTIVE},
    {"congregation": "c3", "approval": EventApprovalStatus.CONFIRMED, "is_service": True},
    {"group": ("c1", "c2")},
    {"group": ()},
    {"group": ("c1",), "is_service": False},
    {"status": PlanningSlotStatus.CANCELLED, "approval": EventApprovalStatus.PLANNED},
    {"is_service": False},
]


@pytest.mark.parametrize("flt", FILTERS, ids=lambda f: ",".join(f) or "none")
async def test_sql_listing_matches_in_memory_semantics(sessions, tenant, flt) -> None:
    start, end = DAY - timedelta(days=1), DAY + timedelta(days=30)
    cong = tenant[flt["congregation"]] if "congregation" in flt else None
    group = {tenant[k] for k in flt["group"]} if "group" in flt else None
    async with sessions() as db:
        repo = SqlPlanningSlotRepository(db)
        everything = await repo.list_for_date_range(
            district_id=tenant["district"], from_date=start, to_date=end
        )
        expected = _reference(
            everything,
            congregation_id=cong, group_ids=group, only_district=flt.get("only_district", False),
            status=flt.get("status"), approval=flt.get("approval"), is_service=flt.get("is_service"),
        )
        kwargs = {
            "district_id": tenant["district"], "from_date": start, "to_date": end,
            "congregation_id": cong, "group_congregation_ids": group,
            "only_district_level": flt.get("only_district", False),
            "status": flt.get("status"), "approval_status": flt.get("approval"),
            "is_service": flt.get("is_service"), "service_category": SERVICE_CATEGORY,
        }
        page_size = 7
        seen: list[uuid.UUID] = []
        for offset in range(0, max(len(expected), 1) + page_size, page_size):
            page, total = await repo.list_page(limit=page_size, offset=offset, **kwargs)
            assert total == len(expected)
            assert len(page) <= page_size
            seen.extend(s.id for s in page)
    assert len(seen) == len(set(seen))  # pages never overlap
    assert set(seen) == {s.id for s in expected}  # nothing missing, nothing extra


async def test_listing_never_includes_other_districts(sessions, tenant) -> None:
    async with sessions() as db:
        page, total = await SqlPlanningSlotRepository(db).list_page(
            district_id=tenant["district"], from_date=DAY - timedelta(days=1),
            to_date=DAY + timedelta(days=30), limit=500, offset=0,
        )
    assert total == len(page)
    assert all(s.district_id == tenant["district"] for s in page)
