# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Database-backed reminder flow with live memberships and monthly deduplication.

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, time

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.orm_models.district_reminder_config import ReminderDeliveryORM
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.user import UserORM
from app.adapters.db.repositories.district_reminder_config import (
    SqlDistrictReminderConfigRepository,
)
from app.adapters.db.session import _set_tenant_gucs
from app.adapters.mail.mock import MockMailService
from app.application.reminder_service import dispatch_reminders
from app.application.tasks import _run_as_system_worker
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.models.role import Role


@pytest.mark.asyncio
async def test_full_monthly_reminder_flow() -> None:
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_async_engine(db_url, pool_pre_ping=True)
    # Mirror production RLS setup after every transaction and intermediate commit.
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    district_id = uuid.uuid4()
    another_district_id = uuid.uuid4()
    matching_user = f"reminder-test-{uuid.uuid4()}"
    outside_user = f"reminder-test-{uuid.uuid4()}"
    now = datetime(2026, 3, 15, 12, tzinfo=UTC)
    config = DistrictReminderConfig.create(
        district_id=district_id,
        day_of_month=15,
        time_of_day=time(10),
        subject_template="{district_name}: {month}",
        body_template="Termin: {day}. {year}",
        recipient_role=Role.PLANNER,
    )

    async def run_with_worker_context(operation):
        return await _run_as_system_worker(operation())

    async def seed() -> None:
        async with sessions() as db:
            for id_, name in ((district_id, "Bezirk Mitte"), (another_district_id, "Anderer Bezirk")):
                db.add(DistrictORM(id=id_, name=name, created_at=now, updated_at=now))
            for sub, email in (
                (matching_user, "matching@example.org"),
                (outside_user, "outside@example.org"),
            ):
                db.add(UserORM(
                    id=uuid.uuid4(), sub=sub, email=email, username=sub,
                    is_superadmin=False, created_at=now, updated_at=now,
                ))
            # These ORM classes have no mapped relationships. Flush principals
            # explicitly so that FK inserts never depend on flush ordering.
            await db.flush()
            for sub, scope_id in ((matching_user, district_id), (outside_user, another_district_id)):
                db.add(MembershipORM(
                    id=uuid.uuid4(), user_sub=sub, role=Role.PLANNER.value,
                    scope_type="DISTRICT", scope_id=scope_id,
                    created_at=now, updated_at=now,
                ))
            await db.flush()
            await SqlDistrictReminderConfigRepository(db).save(config)
            await db.commit()

    async def verify() -> None:
        mail = MockMailService()
        async with sessions() as db:
            first = await dispatch_reminders(db, mail, now=now)
            second = await dispatch_reminders(db, mail, now=now)
            assert first["sent"] == 1
            assert second["sent"] == 0
            assert [record.to for record in mail.sent] == [("matching@example.org",)]
            assert mail.sent[0].subject == "Bezirk Mitte: März"
            deliveries = (
                await db.execute(
                    select(ReminderDeliveryORM).where(ReminderDeliveryORM.reminder_id == config.id)
                )
            ).scalars().all()
            assert len(deliveries) == 1
            assert deliveries[0].sent_at is not None

    async def cleanup() -> None:
        async with sessions() as db:
            await db.execute(text("DELETE FROM reminder_deliveries WHERE reminder_id = :id"), {"id": config.id})
            await db.execute(text("DELETE FROM district_reminder_config WHERE id = :id"), {"id": config.id})
            await db.execute(
                text("DELETE FROM memberships WHERE user_sub IN (:first, :second)"),
                {"first": matching_user, "second": outside_user},
            )
            await db.execute(
                text("DELETE FROM users WHERE sub IN (:first, :second)"),
                {"first": matching_user, "second": outside_user},
            )
            await db.execute(
                text("DELETE FROM districts WHERE id IN (:first, :second)"),
                {"first": district_id, "second": another_district_id},
            )
            await db.commit()

    try:
        await run_with_worker_context(seed)
        await run_with_worker_context(verify)
    finally:
        try:
            await run_with_worker_context(cleanup)
        finally:
            await engine.dispose()
