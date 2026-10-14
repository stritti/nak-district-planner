# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Reject malformed recurrence intervals and preserve the scheduled batch."""

import uuid
from datetime import date, time
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.planning_series import (
    PlanningSeriesCreate,
    PlanningSeriesUpdate,
)
from app.application.planning_series_generator import PlanningSeriesGenerator
from app.domain.models.planning_series import PlanningSeries


@pytest.mark.parametrize("interval", [0, -1, "2", 1.5, True, None])
def test_create_and_update_reject_invalid_intervals(interval: object) -> None:
    invalid = {"type": "weekly", "interval": interval}
    with pytest.raises(ValidationError, match="Recurrence interval"):
        PlanningSeriesCreate(
            district_id=uuid.uuid4(),
            default_planning_time=time(10),
            recurrence_pattern=invalid,
        )
    with pytest.raises(ValidationError, match="Recurrence interval"):
        PlanningSeriesUpdate(recurrence_pattern=invalid)


def test_create_and_update_accept_biweekly_recurrence() -> None:
    pattern = {"type": "weekly", "interval": 2, "days": [0]}
    create = PlanningSeriesCreate(
        district_id=uuid.uuid4(),
        default_planning_time=time(10),
        recurrence_pattern=pattern,
    )
    update = PlanningSeriesUpdate(recurrence_pattern=pattern)
    assert create.recurrence_pattern == pattern
    assert update.recurrence_pattern == pattern


@pytest.mark.asyncio
async def test_invalid_persisted_series_does_not_block_other_districts(caplog) -> None:
    invalid = PlanningSeries.create(
        district_id=uuid.uuid4(),
        default_planning_time=time(10),
        active_from=date(2026, 6, 1),
        recurrence_pattern={"type": "weekly", "interval": "two", "days": [0]},
    )
    valid = PlanningSeries.create(
        district_id=uuid.uuid4(),
        default_planning_time=time(10),
        active_from=date(2026, 6, 1),
        recurrence_pattern={"type": "weekly", "days": [0]},
    )
    series_repo = AsyncMock()
    series_repo.list_active.return_value = [invalid, valid]
    slot_repo = AsyncMock()
    slot_repo.list_by_generation_keys.return_value = []
    slot_repo.list_deleted_generation_keys.return_value = set()
    slot_repo.get_by_series_date.return_value = None
    slot_repo.add_if_absent.return_value = True
    instance_repo = AsyncMock()

    result = await PlanningSeriesGenerator(
        series_repo=series_repo, slot_repo=slot_repo, instance_repo=instance_repo
    ).run_for_window(from_date=date(2026, 6, 1), to_date_exclusive=date(2026, 6, 2))

    assert result == {"series_processed": 2, "slots_created": 1, "slots_skipped": 1}
    slot_repo.add_if_absent.assert_awaited_once()
    instance_repo.save.assert_awaited_once()
    assert str(invalid.id) in caplog.text


def test_invalid_interval_rejected_by_expansion() -> None:
    from app.application.planning_series_generator import _expand_recurrence

    series = PlanningSeries.create(
        district_id=uuid.uuid4(),
        default_planning_time=time(10),
        recurrence_pattern={"type": "weekly", "interval": True, "days": [0]},
    )
    with pytest.raises(ValueError, match="Recurrence interval"):
        _expand_recurrence(
            series, from_date=date(2026, 6, 1),
            to_date_exclusive=date(2026, 6, 2),
        )
