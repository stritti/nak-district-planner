# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""ICS sync against PostgreSQL: series expansion, idempotency and window-bounded deletion (#465).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.db.session import _set_tenant_gucs
from app.application.sync_service import SyncResult, run_sync
from app.tenant import TenantContext

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ics"
SPRING = datetime(2026, 3, 1, tzinfo=UTC)
SUMMER = datetime(2026, 6, 15, tzinfo=UTC)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)

# Planning slots store UTC wall-clock times; the feed is in Europe/Berlin.
SLOTS = {
    "sunday_cet": (date(2026, 3, 8), time(9, 0)),
    "sunday_cest": (date(2026, 3, 29), time(8, 0)),
    "easter_override": (date(2026, 4, 5), time(7, 30)),
    "floating_choir": (date(2026, 4, 1), time(17, 30)),
    "aemterstunde": (date(2026, 4, 10), time(17, 0)),
    "jahresfest": (date(2028, 6, 4), time(8, 0)),
}


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    TenantContext.set_context(user_sub="system:test", user_roles=["SYSTEM_WORKER"])
    yield async_sessionmaker(engine, expire_on_commit=False)
    TenantContext.clear_context()
    await engine.dispose()


async def _seed(db, district_id, congregation_id, integration_id, slot_ids):
    now = datetime.now(UTC)
    await db.execute(
        text("INSERT INTO districts (id, name, created_at, updated_at) VALUES (:id, 'Bezirk Süd', :n, :n)"),
        {"id": district_id, "n": now},
    )
    await db.execute(
        text(
            "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
            "VALUES (:id, 'Gemeinde Mitte', :d, :n, :n)"
        ),
        {"id": congregation_id, "d": district_id, "n": now},
    )
    await db.execute(
        text(
            "INSERT INTO calendar_integrations (id, district_id, congregation_id, name, type, "
            "credentials_enc, sync_interval, capabilities, is_active, delete_behavior, "
            "created_at, updated_at) VALUES (:id, :d, :c, 'Gemeinde Mitte ICS', 'ICS', 'enc', 60, "
            "'{READ}', true, 'MARK_CANCELLED', :n, :n)"
        ),
        {"id": integration_id, "d": district_id, "c": congregation_id, "n": now},
    )
    for name, (day, at) in SLOTS.items():
        await db.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, congregation_id, category, title, "
                "planning_date, planning_time, status, applicability, created_at, updated_at) "
                "VALUES (:id, :d, :c, 'Gottesdienst', :t, :day, :at, 'ACTIVE', '{}', :n, :n)"
            ),
            {"id": slot_ids[name], "d": district_id, "c": congregation_id, "t": name,
             "day": day, "at": at, "n": now},
        )
    await db.commit()


def _connector(feed: str) -> ICalConnector:
    response = MagicMock(content=(FIXTURES / feed).read_bytes(), headers={"content-type": "text/calendar"})
    response.raise_for_status = MagicMock()
    return ICalConnector(client=AsyncMock(get=AsyncMock(return_value=response)))


async def test_ics_series_sync_is_idempotent_and_reconciles_only_inside_window(sessions):
    district_id, congregation_id, integration_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    slot_ids = {name: uuid.uuid4() for name in SLOTS}

    async def sync(feed: str, now: datetime) -> SyncResult:
        async with sessions() as db:
            with (
                patch("app.application.sync_service._get_connector", return_value=_connector(feed)),
                patch("app.application.sync_service.decrypt_credentials", return_value={"url": "https://x/c.ics"}),
            ):
                result = await run_sync(integration_id, db, now=now)
            await db.commit()
            return result

    async def scalar(sql: str):
        async with sessions() as db:
            return (await db.execute(text(sql), {"i": integration_id, "d": district_id})).scalar_one()

    async def slot_status() -> dict[str, str]:
        async with sessions() as db:
            rows = await db.execute(
                text("SELECT title, status FROM planning_slots WHERE district_id = :d"), {"d": district_id}
            )
            return dict(rows.all())

    try:
        async with sessions() as db:
            await _seed(db, district_id, congregation_id, integration_id, slot_ids)

        first = await sync("gemeinde_mitte.ics", SPRING)
        assert first.auto_matched == 5  # all slots except the far-future Jahresfest
        assert first.failed == 0
        linked = await scalar(
            "SELECT string_agg(external_event_id, ',' ORDER BY external_event_id) "
            "FROM external_event_links WHERE calendar_integration_id = :i"
        )
        assert "gd-sonntag-0001@gemeinde-mitte.example::20260329T080000Z" in linked
        assert "gd-sonntag-0001@gemeinde-mitte.example::20260405T080000Z" in linked
        candidates = await scalar(
            "SELECT count(*) FROM external_event_candidates WHERE calendar_integration_id = :i"
        )

        second = await sync("gemeinde_mitte.ics", SPRING)
        assert (second.created, second.updated, second.cancelled, second.auto_matched) == (0, 0, 0, 0)
        assert second.skipped == first.auto_matched + first.skipped
        assert await scalar(
            "SELECT count(*) FROM external_event_candidates WHERE calendar_integration_id = :i"
        ) == candidates

        # A later run links the Jahresfest once it enters the window.
        assert (await sync("gemeinde_mitte.ics", SUMMER)).auto_matched == 1

        # Ämterstunde disappears from the feed; Jahresfest is outside the spring window.
        removed = await sync("gemeinde_mitte_aemterstunde_removed.ics", SPRING)
        assert (removed.cancelled, removed.updated) == (1, 0)
        statuses = await slot_status()
        assert statuses.pop("aemterstunde") == "CANCELLED"
        assert set(statuses.values()) == {"ACTIVE"}

        # Codex #483: a temporary feed omission must not cancel permanently.
        restored = await sync("gemeinde_mitte.ics", SPRING)
        assert (restored.cancelled, restored.updated) == (0, 1)
        assert set((await slot_status()).values()) == {"ACTIVE"}
        assert (await sync("gemeinde_mitte.ics", SPRING)).updated == 0
    finally:
        async with sessions() as db:
            for sql in (
                "DELETE FROM notifications WHERE district_id = :d",
                "DELETE FROM calendar_integrations WHERE id = :i",
                "DELETE FROM event_instances WHERE planning_slot_id IN "
                "(SELECT id FROM planning_slots WHERE district_id = :d)",
                "DELETE FROM planning_slots WHERE district_id = :d",
                "DELETE FROM congregations WHERE district_id = :d",
                "DELETE FROM districts WHERE id = :d",
            ):
                await db.execute(text(sql), {"d": district_id, "i": integration_id})
            await db.commit()
