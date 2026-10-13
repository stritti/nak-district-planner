# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Typed application command contracts without HTTP schema dependencies."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.calendar_integration_commands import CalendarIntegrationUpdateCommand
from app.application.services.calendar_integration_service import CalendarIntegrationService


@pytest.mark.asyncio
async def test_update_distinguishes_omitted_from_explicit_null() -> None:
    integration = SimpleNamespace(
        name="Original", credentials_enc="secret", sync_interval=60,
        capabilities=[], default_category="Gottesdienst",
        delete_behavior="mark_cancelled", updated_at=None,
    )
    repository = AsyncMock()
    command = CalendarIntegrationUpdateCommand(
        name=None, default_category=None,
        provided_fields=frozenset({"name", "default_category"}),
    )

    result = await CalendarIntegrationService(repository).update_integration(
        integration, command
    )

    assert result.name == "Original"  # null does not rename
    assert result.default_category is None  # explicit null clears nullable category
    assert result.sync_interval == 60  # omitted values stay unchanged
    repository.save.assert_awaited_once_with(integration)


@pytest.mark.asyncio
async def test_update_applies_typed_values_without_dictionary_lookup() -> None:
    integration = SimpleNamespace(
        name="Original", credentials_enc="secret", sync_interval=60,
        capabilities=[], default_category="Gottesdienst",
        delete_behavior="mark_cancelled", updated_at=None,
    )
    repository = AsyncMock()
    command = CalendarIntegrationUpdateCommand(
        name="Updated", sync_interval=120,
        provided_fields=frozenset({"name", "sync_interval"}),
    )

    result = await CalendarIntegrationService(repository).update_integration(
        integration, command
    )

    assert result.name == "Updated"
    assert result.sync_interval == 120
    assert result.default_category == "Gottesdienst"
    repository.save.assert_awaited_once_with(integration)
