# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Isolated regression tests for monthly reminder dispatch orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.mail.mock import MockMailService
from app.application.reminder_service import dispatch_reminders
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.models.role import Role
from app.domain.ports.mail import MailDeliveryError


def reminder(*, active: bool = True, day: int = 15) -> DistrictReminderConfig:
    return DistrictReminderConfig.create(
        district_id=uuid.uuid4(), day_of_month=day, time_of_day=time(10),
        subject_template="{district_name}: {month}", body_template="Am {day}. {year}",
        recipient_role=Role.PLANNER, is_active=active,
    )


@pytest.mark.asyncio
async def test_due_reminder_is_sent_once_per_claimed_recipient() -> None:
    config = reminder()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(name="Bezirk Mitte")
    claimed_id = uuid.uuid4()
    session.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda: claimed_id), MagicMock()]
    mail = MockMailService()
    with (
        patch("app.application.reminder_service.SqlDistrictReminderConfigRepository") as repository,
        patch("app.application.reminder_service.recipient_emails", new_callable=AsyncMock) as recipients,
    ):
        repository.return_value.list_active = AsyncMock(return_value=[config])
        recipients.return_value = ["one@example.org"]
        summary = await dispatch_reminders(session, mail, now=datetime(2026, 3, 15, 12, tzinfo=UTC))
    assert summary == {"evaluated": 1, "sent": 1, "skipped": 0, "failed": 0}
    assert len(mail.sent) == 1
    assert mail.sent[0].subject == "Bezirk Mitte: März"
    assert mail.sent[0].body == "Am 15. 2026"
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_reminder_with_no_recipients_skips_dispatch() -> None:
    config = reminder()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(name="Bezirk Mitte")
    with (
        patch("app.application.reminder_service.SqlDistrictReminderConfigRepository") as repository,
        patch("app.application.reminder_service.recipient_emails", new_callable=AsyncMock) as recipients,
    ):
        repository.return_value.list_active = AsyncMock(return_value=[config])
        recipients.return_value = []
        summary = await dispatch_reminders(session, MockMailService(), now=datetime(2026, 3, 15, 12, tzinfo=UTC))
    assert summary == {"evaluated": 1, "sent": 0, "skipped": 1, "failed": 0}
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_monthly_claim_prevents_duplicate_send() -> None:
    config = reminder()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(name="Bezirk Mitte")
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    mail = MockMailService()
    with (
        patch("app.application.reminder_service.SqlDistrictReminderConfigRepository") as repository,
        patch("app.application.reminder_service.recipient_emails", new_callable=AsyncMock) as recipients,
    ):
        repository.return_value.list_active = AsyncMock(return_value=[config])
        recipients.return_value = ["one@example.org"]
        summary = await dispatch_reminders(session, mail, now=datetime(2026, 3, 15, 12, tzinfo=UTC))
    assert summary["skipped"] == 1
    assert mail.sent == []


@pytest.mark.asyncio
async def test_mail_failure_does_not_abort_remaining_recipients() -> None:
    config = reminder()
    session = AsyncMock()
    session.get.return_value = SimpleNamespace(name="Bezirk Mitte")
    session.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: uuid.uuid4()),
        SimpleNamespace(scalar_one_or_none=lambda: uuid.uuid4()),
        MagicMock(),
    ]
    mail = MagicMock()
    mail.send.side_effect = [MailDeliveryError("offline"), None]
    with (
        patch("app.application.reminder_service.SqlDistrictReminderConfigRepository") as repository,
        patch("app.application.reminder_service.recipient_emails", new_callable=AsyncMock) as recipients,
    ):
        repository.return_value.list_active = AsyncMock(return_value=[config])
        recipients.return_value = ["one@example.org", "two@example.org"]
        summary = await dispatch_reminders(session, mail, now=datetime(2026, 3, 15, 12, tzinfo=UTC))
    assert summary == {"evaluated": 1, "sent": 1, "skipped": 0, "failed": 1}
    assert mail.send.call_count == 2


@pytest.mark.asyncio
async def test_inactive_or_not_due_config_is_not_sent() -> None:
    config = reminder(day=16)
    session = AsyncMock()
    with patch("app.application.reminder_service.SqlDistrictReminderConfigRepository") as repository:
        repository.return_value.list_active = AsyncMock(return_value=[config])
        summary = await dispatch_reminders(session, MockMailService(), now=datetime(2026, 3, 15, 12, tzinfo=UTC))
    assert summary["skipped"] == 1
    session.get.assert_not_awaited()
