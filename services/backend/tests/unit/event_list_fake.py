# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""In-memory stand-in for ``SqlPlanningSlotRepository.list_page`` (#604).

The SQL filters are verified against PostgreSQL in
``tests/integration/test_event_listing_postgres.py``; API-level tests with mocked
repositories use this fake so they keep exercising the router wiring.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus


def fake_list_page(slots: list[PlanningSlot]) -> AsyncMock:
    async def list_page(
        *,
        limit,
        offset,
        congregation_id=None,
        group_congregation_ids=None,
        only_district_level=False,
        status=None,
        approval_status=None,
        is_service=None,
        service_category="",
        **_,
    ):
        found = list(slots)
        if group_congregation_ids is not None:
            found = [
                s for s in found if s.congregation_id is None or s.congregation_id in group_congregation_ids
            ]
        if only_district_level:
            found = [s for s in found if s.congregation_id is None]
        elif congregation_id is not None:
            found = [
                s
                for s in found
                if s.congregation_id == congregation_id
                or (s.status == PlanningSlotStatus.ACTIVE and s.is_distributed_to(congregation_id))
            ]
        if status is not None:
            found = [s for s in found if s.status == status]
        if approval_status is not None:
            found = [s for s in found if s.approval_status == approval_status]
        if is_service is not None:
            found = [s for s in found if (s.category == service_category) == is_service]
        return found[offset : offset + limit], len(found)

    return AsyncMock(side_effect=list_page)
