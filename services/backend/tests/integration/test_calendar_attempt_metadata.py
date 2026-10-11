# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Integration tests for the attempt-metadata UPDATE in #470 (#568 review)."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.calendar_integration import (
    SqlCalendarIntegrationRepository,
)
from app.adapters.db.session import _set_tenant_gucs
from app.domain.models.membership import TenantContext

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    from sqlalchemy import event

    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    TenantContext.set_context(user_sub="system:test", user_roles=["SYSTEM_WORKER"])
    yield async_sessionmaker(engine, expire_on_commit=False)
    TenantContext.clear_context()
    await engine.dispose()


async def _seed(db, integration_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    district_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO districts (id, name, created_at, updated_at) "
            "VALUES (:id, 'Bezirk Attempt', :n, :n)"
        ),
        {"id": district_id, "n": now},
    )
    await db.execute(
        text(
            "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
            "VALUES (:id, 'Gemeinde Attempt', :d, :n, :n)"
        ),
        {"id": uuid.uuid4(), "d": district_id, "n": now},
    )
    await db.execute(
        text(
            "INSERT INTO calendar_integrations (id, district_id, congregation_id, name, type, "
            "credentials_enc, sync_interval, capabilities, is_active, delete_behavior, "
            "created_at, updated_at) VALUES (:id, :d, NULL, 'Attempt ICS', 'ICS', 'enc', 5, "
            "'{READ}', true, 'MARK_CANCELLED', :n, :n)"
        ),
        {"id": integration_id, "d": district_id, "n": now},
    )
    await db.commit()


async def _row(db, integration_id: uuid.UUID) -> dict:
    result = await db.execute(
        text(
            "SELECT last_attempt_at, last_synced_at, last_sync_error, sync_interval, name, "
            "is_active, updated_at FROM calendar_integrations WHERE id = :id"
        ),
        {"id": integration_id},
    )
    return dict(result.mappings().one())


async def test_record_attempt_persists_error_and_timestamp(sessions):
    integration_id = uuid.uuid4()
    async with sessions() as db:
        await _seed(db, integration_id)

    at = datetime.now(UTC) - timedelta(minutes=1)
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        updated = await repo.record_attempt(
            integration_id, at, "Synchronisierung fehlgeschlagen (CalendarConnectorError)"
        )
        await db.commit()
        assert updated is True

    async with sessions() as db:
        row = await _row(db, integration_id)
        assert row["last_attempt_at"] == at
        assert row["last_sync_error"] == "Synchronisierung fehlgeschlagen (CalendarConnectorError)"
        assert row["last_synced_at"] is None

    async with sessions() as db:
        await db.execute(
            text("DELETE FROM calendar_integrations WHERE id = :id"), {"id": integration_id}
        )
        await db.commit()


async def test_record_attempt_clears_error_only_without_newer_failure(sessions):
    integration_id = uuid.uuid4()
    async with sessions() as db:
        await _seed(db, integration_id)

    failure_at = datetime.now(UTC) - timedelta(minutes=10)
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        await repo.record_attempt(integration_id, failure_at, "Synchronisierung fehlgeschlagen (X)")
        await db.commit()

    later_error_at = failure_at + timedelta(minutes=1)
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        await repo.record_attempt(integration_id, later_error_at, "Synchronisierung fehlgeschlagen (Y)")
        await db.commit()

    async with sessions() as db:
        row = await _row(db, integration_id)
        assert row["last_attempt_at"] == later_error_at
        assert row["last_sync_error"] == "Synchronisierung fehlgeschlagen (Y)"

    success_at = later_error_at + timedelta(minutes=1)
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        await repo.record_attempt(integration_id, success_at, None)
        await db.commit()

    async with sessions() as db:
        row = await _row(db, integration_id)
        assert row["last_attempt_at"] == success_at
        assert row["last_sync_error"] is None

    stale_success_at = failure_at - timedelta(minutes=1)
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        await repo.record_attempt(integration_id, stale_success_at, None)
        await db.commit()

    async with sessions() as db:
        row = await _row(db, integration_id)
        assert row["last_attempt_at"] == success_at
        assert row["last_sync_error"] is None

    async with sessions() as db:
        await db.execute(
            text("DELETE FROM calendar_integrations WHERE id = :id"), {"id": integration_id}
        )
        await db.commit()


async def test_record_attempt_preserves_success_and_never_touches_other_columns(sessions):
    integration_id = uuid.uuid4()
    async with sessions() as db:
        await _seed(db, integration_id)

    now = datetime.now(UTC)
    async with sessions() as db:
        await db.execute(
            text(
                "UPDATE calendar_integrations SET last_synced_at = :s, last_sync_error = NULL, "
                "sync_interval = 42, name = 'Umbenannt', is_active = false, "
                "updated_at = :u WHERE id = :id"
            ),
            {"s": now, "u": now, "id": integration_id},
        )
        await db.commit()

    async with sessions() as db:
        before = await _row(db, integration_id)

    at = now + timedelta(seconds=5)
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        await repo.record_attempt(integration_id, at, "Synchronisierung fehlgeschlagen (Z)")
        await db.commit()

    async with sessions() as db:
        after = await _row(db, integration_id)
        assert after["last_attempt_at"] == at
        assert after["last_sync_error"] == "Synchronisierung fehlgeschlagen (Z)"
        for column in ("last_synced_at", "sync_interval", "name", "is_active", "updated_at"):
            assert after[column] == before[column], f"record_attempt must not touch {column}"

    async with sessions() as db:
        await db.execute(
            text("DELETE FROM calendar_integrations WHERE id = :id"), {"id": integration_id}
        )
        await db.commit()


async def test_record_attempt_reports_missing_integration(sessions):
    missing = uuid.uuid4()
    async with sessions() as db:
        repo = SqlCalendarIntegrationRepository(db)
        updated = await repo.record_attempt(missing, datetime.now(UTC), None)
        assert updated is False
        await db.commit()
