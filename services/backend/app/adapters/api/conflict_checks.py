# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Adapter wiring for the service-assignment conflict check.

The check also considers the leader's organisational duties; the lookup that finds
them lives in the persistence adapter and is injected here.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository
from app.application.service_assignment_conflict import (
    check_service_assignment_conflicts as _check_service_assignment_conflicts,
)


async def check_service_assignment_conflicts(session: AsyncSession, **kwargs) -> list:
    """The application check with the duty lookup of the SQL adapter injected."""
    return await _check_service_assignment_conflicts(
        session,
        duty_lookup=SqlEventDutiesRepository(session).list_identity_schedule,
        **kwargs,
    )
