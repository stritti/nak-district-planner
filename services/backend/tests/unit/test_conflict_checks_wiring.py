# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""The adapter-level conflict check injects the SQL duty lookup into the application check."""

from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.api import conflict_checks


@pytest.mark.asyncio
async def test_the_duty_lookup_of_the_sql_adapter_is_injected():
    session = AsyncMock()
    with (
        patch.object(conflict_checks, "_check_service_assignment_conflicts", AsyncMock(return_value=["x"])) as inner,
        patch.object(conflict_checks, "SqlEventDutiesRepository") as repository,
    ):
        result = await conflict_checks.check_service_assignment_conflicts(
            session, event_id="e", leader_id="l"
        )
    assert result == ["x"]
    repository.assert_called_once_with(session)
    inner.assert_awaited_once_with(
        session,
        duty_lookup=repository.return_value.list_identity_schedule,
        event_id="e",
        leader_id="l",
    )
