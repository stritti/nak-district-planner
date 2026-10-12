# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression tests: API and scheduled tasks use the generator's current constructor."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.api.routers.districts import generate_planning_series_slots as api_generate
from app.adapters.worker.tasks import generate_planning_series_slots as beat_generate


@pytest.mark.asyncio
async def test_manual_generate_passes_only_supported_repositories() -> None:
    district_id = uuid.uuid4()
    district_repo = MagicMock()
    district_repo.get = AsyncMock(return_value=object())
    series_repo = MagicMock()
    slot_repo = MagicMock()
    instance_repo = MagicMock()
    session = AsyncMock()
    expected = {"series_processed": 1, "slots_created": 2, "slots_skipped": 0}
    with (
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch("app.adapters.api.routers.districts.PlanningSeriesGenerator") as generator,
    ):
        generator.return_value.run_for_window = AsyncMock(return_value=expected)
        actual = await api_generate(
            district_id=district_id,
            auth=MagicMock(),
            db=session,
            from_dt=datetime(2026, 6, 1, tzinfo=UTC),
            to_dt=datetime(2026, 6, 30, tzinfo=UTC),
            district_repo=district_repo,
            congregation_repo=MagicMock(),
            series_repo=series_repo,
            slot_repo=slot_repo,
            instance_repo=instance_repo,
        )

    assert actual == expected
    generator.assert_called_once_with(
        series_repo=series_repo, slot_repo=slot_repo, instance_repo=instance_repo
    )
    session.commit.assert_awaited_once()


def test_scheduled_generate_passes_only_supported_repositories() -> None:
    session = AsyncMock()
    summary = {"series_processed": 1, "slots_created": 2, "slots_skipped": 0}
    with (
        patch("app.config.settings") as settings,
        patch("app.adapters.db.session.AsyncSessionLocal") as session_factory,
        patch("app.adapters.db.repositories.planning_series.SqlPlanningSeriesRepository")
        as series_repo,
        patch("app.adapters.db.repositories.planning_slot.SqlPlanningSlotRepository")
        as slot_repo,
        patch("app.adapters.db.repositories.event_instance.SqlEventInstanceRepository")
        as instance_repo,
        patch("app.application.planning_series_generator.PlanningSeriesGenerator") as generator,
        patch("app.adapters.worker.tasks._run_as_system_worker", side_effect=lambda work: work),
    ):
        settings.use_series_generation = True
        session_factory.return_value.__aenter__.return_value = session
        generator.return_value.run = AsyncMock(return_value=summary)
        actual = beat_generate()

    assert actual == summary
    generator.assert_called_once_with(
        series_repo=series_repo.return_value,
        slot_repo=slot_repo.return_value,
        instance_repo=instance_repo.return_value,
    )
    session.commit.assert_awaited_once()
