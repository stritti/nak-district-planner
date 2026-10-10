# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Celery entry point for the daily SLOT_UNASSIGNED scan."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from app.celery_app import celery

# Service dates are local calendar days of the districts.
LOCAL_TIMEZONE = ZoneInfo("Europe/Berlin")


@celery.task(name="scan_slot_gaps")
def scan_slot_gaps() -> dict[str, int]:
    from app.adapters.db.repositories.slot_gap import SqlSlotGapLedger
    from app.adapters.db.session import AsyncSessionLocal
    from app.adapters.db.transactional_events import publish_after_commit
    from app.application.slot_gap_scan import SlotGapScanner
    from app.application.tasks import _run_as_system_worker
    from app.config import settings

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            scanner = SlotGapScanner(
                ledger=SqlSlotGapLedger(session),
                # Ledger and events commit together: no mail for an unrecorded
                # report, no report without its mail being queued.
                publish=lambda event: publish_after_commit(session, event),
                horizon_days=settings.slot_gap_scan_days,
            )
            summary = await scanner.scan(datetime.now(LOCAL_TIMEZONE).date())
            await session.commit()
            return asdict(summary)

    return asyncio.run(_run_as_system_worker(_run()))
