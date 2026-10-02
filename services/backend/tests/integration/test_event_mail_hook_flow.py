"""Database-backed event → hook → mail flow with real repositories.

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.user import UserORM
from app.adapters.db.repositories.event_mail_hook import (
    SqlEventMailHookRepository,
    SqlRecipientDirectory,
)
from app.adapters.db.session import _set_tenant_gucs
from app.adapters.db.transactional_events import publish_after_commit
from app.adapters.mail.mock import MockMailService
from app.application.event_mail_hooks import EventMailHookDispatcher
from app.application.tasks import _run_as_system_worker
from app.domain.event_payloads import registration_received
from app.domain.events import DomainEvent, DomainEventBus, EventType
from app.domain.models.event_mail_hook import EventMailHook
from app.domain.models.role import Role


@pytest.mark.asyncio
async def test_committed_event_mails_matching_role_and_rollback_mails_nothing() -> None:
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_async_engine(db_url, pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    district_id, other_district_id = uuid.uuid4(), uuid.uuid4()
    admin, planner, foreign_admin = (f"hook-test-{uuid.uuid4()}" for _ in range(3))
    hooks = [
        EventMailHook(
            district_id=district_id,
            event_type=EventType.REGISTRATION_RECEIVED,
            recipient_role=Role.DISTRICT_ADMIN,
            subject_template="{district_name}: {leader_name}",
            body_template="{leader_email}",
        ),
        EventMailHook(  # inactive: must not send
            district_id=district_id,
            event_type=EventType.REGISTRATION_RECEIVED,
            recipient_role=Role.PLANNER,
            subject_template="x",
            body_template="y",
            is_active=False,
        ),
        EventMailHook(  # other event type: must not send
            district_id=district_id,
            event_type=EventType.PLAN_FINALIZED,
            recipient_role=Role.PLANNER,
            subject_template="{month}",
            body_template="{year}",
        ),
    ]
    received: list[DomainEvent] = []
    bus = DomainEventBus()
    bus.subscribe(EventType.REGISTRATION_RECEIVED, received.append)

    async def seed() -> None:
        async with sessions() as db:
            for id_, name in ((district_id, "Bezirk Nord"), (other_district_id, "Bezirk Ost")):
                db.add(DistrictORM(id=id_, name=name, created_at=now, updated_at=now))
            for sub in (admin, planner, foreign_admin):
                db.add(
                    UserORM(
                        id=uuid.uuid4(),
                        sub=sub,
                        email=f"{sub}@example.org",
                        username=sub,
                        is_superadmin=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
            await db.flush()
            for sub, role, scope in (
                (admin, Role.DISTRICT_ADMIN, district_id),
                (planner, Role.PLANNER, district_id),
                (foreign_admin, Role.DISTRICT_ADMIN, other_district_id),
            ):
                db.add(
                    MembershipORM(
                        id=uuid.uuid4(),
                        user_sub=sub,
                        role=role.value,
                        scope_type="DISTRICT",
                        scope_id=scope,
                        created_at=now,
                        updated_at=now,
                    )
                )
            await db.flush()
            for hook in hooks:
                await SqlEventMailHookRepository(db).save(hook)
            await db.commit()

    async def emit_and_dispatch() -> MockMailService:
        async with sessions() as db:
            await db.execute(text("SELECT 1"))
            publish_after_commit(
                db,
                registration_received(district_id, leader_name="Rolled Back", leader_email=None),
                bus,
            )
            await db.rollback()
            await db.execute(text("SELECT 1"))
            publish_after_commit(
                db,
                registration_received(
                    district_id, leader_name="Anna", leader_email="anna@example.org"
                ),
                bus,
            )
            assert received == []
            await db.commit()
        assert [e.payload["leader_name"] for e in received] == ["Anna"]

        mail = MockMailService()
        async with sessions() as db:
            dispatcher = EventMailHookDispatcher(
                SqlEventMailHookRepository(db), SqlRecipientDirectory(db), mail
            )
            summary = await dispatcher.dispatch(received[0])
        assert (summary.hooks, summary.sent, summary.failed) == (1, 1, 0)
        return mail

    async def cleanup() -> None:
        async with sessions() as db:
            await db.execute(
                text("DELETE FROM event_mail_hooks WHERE district_id = :d"), {"d": district_id}
            )
            await db.execute(
                text("DELETE FROM memberships WHERE user_sub LIKE 'hook-test-%'"),
            )
            await db.execute(text("DELETE FROM users WHERE sub LIKE 'hook-test-%'"))
            await db.execute(
                text("DELETE FROM districts WHERE id IN (:a, :b)"),
                {"a": district_id, "b": other_district_id},
            )
            await db.commit()

    try:
        await _run_as_system_worker(seed())
        mail = await _run_as_system_worker(emit_and_dispatch())
        assert [record.to for record in mail.sent] == [(f"{admin}@example.org",)]
        assert mail.sent[0].subject == "Bezirk Nord: Anna"
        assert mail.sent[0].body.startswith("anna@example.org")
    finally:
        await _run_as_system_worker(cleanup())
        await engine.dispose()
