# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit coverage for the monthly district reminder Celery entry point."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.worker import reminder_tasks


def _session_factory(session: MagicMock) -> MagicMock:
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


class TestCheckDueRemindersTask:
    def test_task_dispatches_reminders_and_returns_summary(self) -> None:
        session = MagicMock()
        expected = {"due": 3, "sent": 2, "skipped": 1}
        dispatched = AsyncMock(return_value=expected)
        mail_service = MagicMock()

        with (
            patch("app.adapters.db.session.AsyncSessionLocal", _session_factory(session)),
            patch("app.adapters.mail.create_mail_service", return_value=mail_service),
            patch(
                "app.application.reminder_service.dispatch_reminders",
                dispatched,
            ),
            patch(
                "app.adapters.worker.tasks._run_as_system_worker",
                MagicMock(side_effect=lambda coro: coro),
            ) as system_worker,
        ):
            result = reminder_tasks.check_due_reminders.run()

        assert result == expected
        system_worker.assert_called_once()
        dispatched.assert_awaited_once_with(session, mail_service)

    def test_task_name_is_stable(self) -> None:
        assert reminder_tasks.check_due_reminders.name == "check_due_reminders"
