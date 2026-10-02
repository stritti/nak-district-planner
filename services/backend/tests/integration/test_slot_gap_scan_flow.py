"""Daily gap scan against PostgreSQL: gap rule, ledger lifecycle and mail hook.

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.event_mail_hook import (
    SqlEventMailHookRepository,
    SqlRecipientDirectory,
)
from app.adapters.db.repositories.slot_gap import SqlSlotGapLedger
from app.adapters.db.session import _set_tenant_gucs
from app.adapters.db.transactional_events import publish_after_commit
from app.adapters.mail.mock import MockMailService
from app.application.event_mail_hooks import EventMailHookDispatcher
from app.application.slot_gap_scan import ScanSummary, SlotGapScanner
from app.application.tasks import _run_as_system_worker
from app.domain.events import DomainEvent, DomainEventBus, EventType
from app.domain.models.event_mail_hook import EventMailHook
from app.domain.models.role import Role

TODAY = date(2030, 3, 1)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed(db, district_id, congregation_id, slots: dict[str, uuid.UUID], admin: str):
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
    rows = {
        # name: (date, category, status, invitation copy?, title)
        "gap": ("2030-03-03", "Gottesdienst", "ACTIVE", False, "Festgottesdienst"),
        "assigned": ("2030-03-03", "Gottesdienst", "ACTIVE", False, None),
        "copy": ("2030-03-06", "Gottesdienst", "ACTIVE", True, None),
        "cancelled": ("2030-03-06", "Gottesdienst", "CANCELLED", False, None),
        "holiday": ("2030-03-10", "Feiertag", "ACTIVE", False, None),
        "late": ("2030-06-01", "Gottesdienst", "ACTIVE", False, None),
    }
    for hour, (name, (day, category, status, copy, title)) in enumerate(rows.items(), start=8):
        await db.execute(
            text(
                "INSERT INTO planning_slots (id, district_id, congregation_id, category, title, "
                "planning_date, planning_time, status, invitation_source_event_id, applicability, "
                "created_at, updated_at) VALUES (:id, :d, :c, :cat, :title, :day, "
                "make_time(:hour, 0, 0), :status, :src, '{}', :n, :n)"
            ),
            {
                "id": slots[name],
                "d": district_id,
                "c": congregation_id,
                "cat": category,
                "title": title,
                "day": date.fromisoformat(day),
                "status": status,
                "hour": hour,
                "src": slots["gap"] if copy else None,
                "n": now,
            },
        )
    await db.execute(
        text(
            "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_name, status, "
            "created_at, updated_at) VALUES (:id, :s, :s, 'Pr. Muster', 'ASSIGNED', :n, :n)"
        ),
        {"id": uuid.uuid4(), "s": slots["assigned"], "n": now},
    )
    await db.execute(
        text(
            "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
            "VALUES (:id, :sub, :email, :sub, false, :n, :n)"
        ),
        {"id": uuid.uuid4(), "sub": admin, "email": f"{admin}@example.org", "n": now},
    )
    await db.execute(
        text(
            "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, "
            "updated_at) VALUES (:id, :sub, 'DISTRICT_ADMIN', 'DISTRICT', :d, :n, :n)"
        ),
        {"id": uuid.uuid4(), "sub": admin, "d": district_id, "n": now},
    )
    await SqlEventMailHookRepository(db).save(
        EventMailHook(
            district_id=district_id,
            event_type=EventType.SLOT_UNASSIGNED,
            recipient_role=Role.DISTRICT_ADMIN,
            subject_template="LÜCKE {congregation_name} am {date}",
            body_template="{event_title} in {district_name} ist nicht besetzt.",
        )
    )
    await db.commit()


async def test_gap_is_reported_once_and_again_after_reopening(sessions) -> None:
    district_id, congregation_id = uuid.uuid4(), uuid.uuid4()
    slots = {name: uuid.uuid4() for name in ("gap", "assigned", "copy", "cancelled", "holiday", "late")}
    admin = f"gap-test-{uuid.uuid4()}"
    bus = DomainEventBus()
    received: list[DomainEvent] = []
    bus.subscribe(EventType.SLOT_UNASSIGNED, received.append)

    async def scan() -> ScanSummary:
        async with sessions() as db:
            scanner = SlotGapScanner(
                SqlSlotGapLedger(db), lambda e: publish_after_commit(db, e, bus), horizon_days=28
            )
            summary = await scanner.scan(TODAY)
            await db.commit()
            return summary

    async def execute(sql: str, **params) -> None:
        async with sessions() as db:
            await db.execute(text(sql), params)
            await db.commit()

    async def scenario() -> MockMailService:
        async with sessions() as db:
            await _seed(db, district_id, congregation_id, slots, admin)

        # Only the unassigned, active service slot inside the window is a gap.
        assert await scan() == ScanSummary(open=1, reported=1, closed=0)
        assert [e.payload for e in received] == [
            {"congregation_name": "Gemeinde Mitte", "date": "2030-03-03", "event_title": "Festgottesdienst"}
        ]
        assert (await scan()).reported == 0  # still open: no second report

        await execute(
            "INSERT INTO service_assignments (id, event_id, planning_slot_id, leader_name, status, "
            "created_at, updated_at) VALUES (:id, :s, :s, 'Pr. Neu', 'ASSIGNED', now(), now())",
            id=uuid.uuid4(),
            s=slots["gap"],
        )
        assert await scan() == ScanSummary(open=0, reported=0, closed=1)

        await execute("DELETE FROM service_assignments WHERE planning_slot_id = :s", s=slots["gap"])
        assert (await scan()).reported == 1  # reopened: reportable again
        assert len(received) == 2

        # Moving the slot to another date is a new gap; the old report is replaced.
        await execute(
            "UPDATE planning_slots SET planning_date = '2030-03-17' WHERE id = :s", s=slots["gap"]
        )
        assert await scan() == ScanSummary(open=1, reported=1, closed=1)
        assert received[-1].payload["date"] == "2030-03-17"

        mail = MockMailService()
        async with sessions() as db:
            dispatcher = EventMailHookDispatcher(
                SqlEventMailHookRepository(db), SqlRecipientDirectory(db), mail
            )
            await dispatcher.dispatch(received[-1])
        return mail

    async def cleanup() -> None:
        async with sessions() as db:
            for sql in (
                "DELETE FROM event_mail_hooks WHERE district_id = :d",
                "DELETE FROM service_assignments WHERE planning_slot_id = ANY(:slots)",
                "DELETE FROM planning_slots WHERE district_id = :d",  # cascades the ledger
                "DELETE FROM congregations WHERE district_id = :d",
                "DELETE FROM memberships WHERE scope_id = :d",
                "DELETE FROM users WHERE sub = :sub",
                "DELETE FROM districts WHERE id = :d",
            ):
                await db.execute(
                    text(sql), {"d": district_id, "slots": list(slots.values()), "sub": admin}
                )
            await db.commit()
            remaining = await db.execute(
                text("SELECT count(*) FROM slot_gap_alerts WHERE district_id = :d"),
                {"d": district_id},
            )
            assert remaining.scalar_one() == 0

    try:
        mail = await _run_as_system_worker(scenario())
        [sent] = mail.sent
        assert sent.to == (f"{admin}@example.org",)
        assert sent.subject == "LÜCKE Gemeinde Mitte am 2030-03-17"
        assert sent.body.startswith("Festgottesdienst in Bezirk Süd ist nicht besetzt.")
    finally:
        await _run_as_system_worker(cleanup())
