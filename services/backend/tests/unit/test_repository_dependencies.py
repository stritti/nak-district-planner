# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.adapters.api.deps import get_calendar_integration_repository
from app.adapters.db.repositories.calendar_integration import (
    SqlCalendarIntegrationRepository,
)


@pytest.mark.asyncio
async def test_calendar_integration_repository_dependency_uses_session() -> None:
    session = AsyncMock()

    repository = await get_calendar_integration_repository(session)

    assert isinstance(repository, SqlCalendarIntegrationRepository)
    assert repository._session is session
