# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Celery entry point for monthly district reminders."""

from __future__ import annotations

import asyncio

from app.celery_app import celery


@celery.task(name="check_due_reminders")
def check_due_reminders() -> dict[str, int]:
    from app.adapters.db.session import AsyncSessionLocal
    from app.adapters.mail import create_mail_service
    from app.application.reminder_service import dispatch_reminders
    from app.application.tasks import _run_as_system_worker

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            return await dispatch_reminders(session, create_mail_service())

    return asyncio.run(_run_as_system_worker(_run()))
