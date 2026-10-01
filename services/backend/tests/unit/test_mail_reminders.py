"""Regression tests for monthly reminder semantics and outbound mail transports."""

from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.api.schemas.reminder_configs import ReminderConfigCreate, ReminderConfigUpdate
from app.adapters.mail import FooterMailService, append_footer, create_mail_service
from app.adapters.mail.log import LogMailService
from app.adapters.mail.mock import MockMailService
from app.adapters.mail.smtp import SmtpMailService
from app.application.reminder_service import render_template
from app.config import Settings
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.models.role import Role
from app.domain.ports.mail import MailDeliveryError


def config(day: int = 31, scheduled: time = time(10, 0), active: bool = True) -> DistrictReminderConfig:
    return DistrictReminderConfig.create(
        district_id=uuid.uuid4(),
        day_of_month=day,
        time_of_day=scheduled,
        subject_template="Planung für {month}",
        body_template="Hallo {district_name}",
        recipient_role=Role.PLANNER,
        is_active=active,
    )


@pytest.mark.parametrize(
    ("timestamp", "due"),
    [
        (datetime(2026, 2, 27, 23, 59), False),
        (datetime(2026, 2, 28, 9, 59), False),
        (datetime(2026, 2, 28, 10), True),
        (datetime(2026, 2, 28, 23, 59), True),
        (datetime(2028, 2, 28, 12), False),
        (datetime(2028, 2, 29, 10), True),
        (datetime(2026, 4, 30, 10), True),
        (datetime(2026, 5, 30, 10), False),
        (datetime(2026, 5, 31, 10), True),
    ],
)
def test_clamping_and_dispatch_time(timestamp: datetime, due: bool) -> None:
    assert config().is_due(timestamp) is due


def test_inactive_config_never_due() -> None:
    assert not config(active=False).is_due(datetime(2026, 2, 28, 12))


@pytest.mark.parametrize("day", [0, -1, 32, 300])
def test_invalid_day_rejected_by_domain_and_api(day: int) -> None:
    with pytest.raises(ValueError):
        config(day=day)
    with pytest.raises(ValueError):
        ReminderConfigCreate(
            day_of_month=day,
            time_of_day="10:00",
            subject_template="subject",
            body_template="body",
            recipient_role="PLANNER",
        )


def test_blank_templates_and_invalid_roles_rejected() -> None:
    with pytest.raises(ValueError):
        DistrictReminderConfig.create(
            district_id=uuid.uuid4(), day_of_month=1, time_of_day=time(10),
            subject_template=" ", body_template="body", recipient_role=Role.PLANNER,
        )
    with pytest.raises(ValueError):
        ReminderConfigCreate(
            day_of_month=1, time_of_day="10:00", subject_template="subject",
            body_template="body", recipient_role="UNKNOWN",
        )
    with pytest.raises(ValueError):
        ReminderConfigUpdate(day_of_month=33)


def test_known_placeholders_substituted_unknown_preserved() -> None:
    result = render_template(
        "{district_name}: {day}. {month} {year}, {unknown}, {{month}}",
        "Bezirk Mitte", date(2026, 3, 15),
    )
    assert result == "Bezirk Mitte: 15. März 2026, {unknown}, {März}"


def test_footer_applied_once_at_composition_root() -> None:
    delegate = MockMailService()
    service = FooterMailService(delegate, "Rechtlicher Hinweis")
    service.send(["one@example.org"], "subject", "body")
    assert delegate.sent[0].body == "body\n---\nRechtlicher Hinweis"
    assert delegate.sent[0].sent_at.tzinfo is UTC
    assert append_footer("body", "") == "body"
    delegate.clear()
    assert delegate.sent == []


def test_log_mail_adapter_records_content(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        LogMailService().send(["one@example.org"], "subject", "body")
    assert "subject" in caplog.text
    assert "body" in caplog.text


def test_factory_selects_transport() -> None:
    for env, expected in [("development", LogMailService), ("test", MockMailService)]:
        service = create_mail_service(Settings(app_env=env, email_footer="footer", _env_file=None))
        assert isinstance(service, FooterMailService)
        assert isinstance(service._delegate, expected)


def test_smtp_delivery_sends_individually_and_deduplicates_recipients() -> None:
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    with patch("app.adapters.mail.smtp.smtplib.SMTP", return_value=smtp):
        service = SmtpMailService(
            host="smtp.example.org", port=587, username="user", password="password",
            from_address="sender@example.org",
        )
        service.send(["one@example.org", "two@example.org", "one@example.org"], "subject", "body")
    assert smtp.starttls.call_count == 1
    smtp.login.assert_called_once_with("user", "password")
    assert smtp.send_message.call_count == 2
    assert {call.args[0]["To"] for call in smtp.send_message.call_args_list} == {
        "one@example.org", "two@example.org"
    }


def test_smtp_failure_is_translated_without_leaking_credentials() -> None:
    with patch("app.adapters.mail.smtp.smtplib.SMTP", side_effect=smtplib.SMTPConnectError(421, "offline")):
        service = SmtpMailService(
            host="smtp.example.org", port=587, username=None, password=None,
            from_address="sender@example.org",
        )
        with pytest.raises(MailDeliveryError, match="SMTP delivery failed"):
            service.send(["one@example.org"], "subject", "body")


def test_smtp_rejects_header_injection_and_incomplete_credentials() -> None:
    with pytest.raises(ValueError):
        SmtpMailService(
            host="smtp.example.org", port=587, username="user", password=None,
            from_address="sender@example.org",
        )
    service = SmtpMailService(
        host="smtp.example.org", port=587, username=None, password=None,
        from_address="sender@example.org",
    )
    with pytest.raises(MailDeliveryError, match="Invalid email header"):
        service.send(["one@example.org"], "subject\nBcc: hidden@example.org", "body")
    service.send([], "subject", "body")
