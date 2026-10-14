# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Router behavior for PlanningSeries; real district RBAC and tenant reference checks."""

from __future__ import annotations

import uuid
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import planning_series as router
from app.adapters.api.schemas.planning_series import PlanningSeriesCreate, PlanningSeriesUpdate
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.role import Role


def _auth(district: uuid.UUID | None, role: Role = Role.DISTRICT_ADMIN,
          *, superadmin: bool = False) -> SimpleNamespace:
    memberships = [] if district is None else [
        Membership.create(
            user_sub="operator", role=role,
            scope_type=ScopeType.DISTRICT, scope_id=district,
        )
    ]
    return SimpleNamespace(
        user_sub="operator", memberships=memberships,
        user=SimpleNamespace(is_superadmin=superadmin),
    )


def _series(district: uuid.UUID) -> PlanningSeries:
    return PlanningSeries.create(
        district_id=district,
        congregation_id=None,
        default_planning_time=time(10, 0),
        recurrence_pattern={"frequency": "weekly", "by_weekday": [6]},
        category="Gottesdienst",
    )


def _series_body(district: uuid.UUID, congregation: uuid.UUID | None = None
                 ) -> PlanningSeriesCreate:
    return PlanningSeriesCreate(
        district_id=district, congregation_id=congregation,
        default_planning_time=time(9, 30),
        recurrence_pattern={"frequency": "weekly"},
        category="Gottesdienst",
        active_from=date(2026, 11, 1),
        is_active=False,
    )


@pytest.mark.asyncio
async def test_create_series_commits_and_preserves_explicit_options() -> None:
    district = uuid.uuid4()
    congregation = uuid.uuid4()
    repo, db = AsyncMock(), AsyncMock()
    db.scalar.return_value = district

    out = await router.create_planning_series(
        _series_body(district, congregation), _auth(district), db, repo=repo,
    )

    assert out.district_id == district
    assert out.congregation_id == congregation
    assert out.recurrence_pattern == {"frequency": "weekly"}
    assert out.is_active is False
    assert out.active_from == date(2026, 11, 1)
    db.scalar.assert_awaited_once()
    db.commit.assert_awaited_once()
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_without_congregation_defaults_to_active_and_empty_recurrence() -> None:
    district = uuid.uuid4()
    repo, db = AsyncMock(), AsyncMock()

    out = await router.create_planning_series(
        PlanningSeriesCreate(
            district_id=district, default_planning_time=time(10),
        ),
        _auth(district), db, repo=repo,
    )

    assert out.is_active is True
    assert out.recurrence_pattern == {}
    db.scalar.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
async def test_create_refuses_invalid_congregation(foreign: bool) -> None:
    district, congregation = uuid.uuid4(), uuid.uuid4()
    repo, db = AsyncMock(), AsyncMock()
    db.scalar.return_value = uuid.uuid4() if foreign else None

    with pytest.raises(HTTPException) as error:
        await router.create_planning_series(
            _series_body(district, congregation), _auth(district), db, repo=repo,
        )

    assert error.value.status_code == 422
    repo.save.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_denies_wrong_district_before_references() -> None:
    district = uuid.uuid4()
    repo, db = AsyncMock(), AsyncMock()

    with pytest.raises(HTTPException) as error:
        await router.create_planning_series(
            _series_body(district, uuid.uuid4()),
            _auth(uuid.uuid4(), Role.DISTRICT_ADMIN), db, repo=repo,
        )
    assert error.value.status_code == 403
    db.scalar.assert_not_awaited()
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_series_missing_and_cross_tenant() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, db = AsyncMock(), AsyncMock()
    repo.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await router.get_planning_series(series.id, _auth(district), db, repo=repo)
    assert missing.value.status_code == 404

    repo.get.return_value = series
    with pytest.raises(HTTPException) as denied:
        await router.get_planning_series(
            series.id, _auth(uuid.uuid4(), Role.DISTRICT_ADMIN), db, repo=repo
        )
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_viewer_gets_series_but_cannot_modify_it() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, db = AsyncMock(), AsyncMock()
    repo.get.return_value = series

    out = await router.get_planning_series(
        series.id, _auth(district, Role.VIEWER), db, repo=repo
    )
    assert out.id == series.id

    with pytest.raises(HTTPException) as denied:
        await router.update_planning_series(
            series.id, PlanningSeriesUpdate(category="Neuer Typ"),
            _auth(district, Role.VIEWER), db, repo=repo,
        )
    assert denied.value.status_code == 403
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_series_not_found() -> None:
    repo = AsyncMock()
    repo.get.return_value = None
    with pytest.raises(HTTPException) as error:
        await router.update_planning_series(
            uuid.uuid4(), PlanningSeriesUpdate(is_active=False),
            _auth(uuid.uuid4()), AsyncMock(), repo=repo,
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_update_all_fields_with_owned_congregation() -> None:
    district, congregation = uuid.uuid4(), uuid.uuid4()
    series = _series(district)
    repo, db = AsyncMock(), AsyncMock()
    repo.get.return_value = series
    db.scalar.return_value = district
    old_updated = series.updated_at

    out = await router.update_planning_series(
        series.id,
        PlanningSeriesUpdate(
            congregation_id=congregation,
            category="Andacht",
            default_planning_time=time(18, 30),
            recurrence_pattern={"frequency": "monthly"},
            active_from=date(2026, 11, 1),
            active_until=date(2027, 11, 1),
            is_active=False,
        ),
        _auth(district), db, repo=repo,
    )

    assert out.congregation_id == congregation
    assert out.category == "Andacht"
    assert out.default_planning_time == time(18, 30)
    assert out.recurrence_pattern == {"frequency": "monthly"}
    assert out.active_from == date(2026, 11, 1)
    assert out.active_until == date(2027, 11, 1)
    assert out.is_active is False
    assert series.updated_at >= old_updated
    db.commit.assert_awaited_once()
    repo.save.assert_awaited_once_with(series)


@pytest.mark.asyncio
async def test_empty_update_does_not_clear_existing_values() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, db = AsyncMock(), AsyncMock()
    repo.get.return_value = series
    old_pattern = series.recurrence_pattern

    out = await router.update_planning_series(
        series.id, PlanningSeriesUpdate(), _auth(district), db, repo=repo
    )
    assert out.recurrence_pattern == old_pattern
    assert out.category == "Gottesdienst"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_rejects_congregation_of_foreign_district() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, db = AsyncMock(), AsyncMock()
    repo.get.return_value = series
    db.scalar.return_value = uuid.uuid4()

    with pytest.raises(HTTPException) as error:
        await router.update_planning_series(
            series.id, PlanningSeriesUpdate(congregation_id=uuid.uuid4()),
            _auth(district), db, repo=repo,
        )
    assert error.value.status_code == 422
    repo.save.assert_not_awaited()
    db.commit.assert_not_awaited()


_GENERATION = {
    "generated": 2, "skipped": 1, "updated": 0,
    "series_processed": 1, "districts_processed": 1,
}


@pytest.mark.asyncio
async def test_single_series_generation_requires_existing_owned_series() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, slots, db = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get.return_value = None

    with pytest.raises(HTTPException) as missing:
        await router.generate_slots_for_series(
            series.id, _auth(district), db,
            series_repo=repo, slot_repo=slots,
        )
    assert missing.value.status_code == 404

    repo.get.return_value = series
    with pytest.raises(HTTPException) as denied:
        await router.generate_slots_for_series(
            series.id, _auth(uuid.uuid4()), db,
            series_repo=repo, slot_repo=slots,
        )
    assert denied.value.status_code == 403
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_single_series_generation_forwards_requested_window() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, slots, db = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get.return_value = series
    request = router.SlotGenerationRequest(
        from_date=date(2026, 12, 1), to_date=date(2026, 12, 31), horizon_months=3
    )

    with patch.object(router, "PlanningSeriesSlotGenerationService") as service_type:
        service_type.return_value.generate_slots_for_series = AsyncMock(
            return_value=_GENERATION
        )
        out = await router.generate_slots_for_series(
            series.id, _auth(district), db, request,
            series_repo=repo, slot_repo=slots,
        )

    assert out.generated == 2
    assert out.skipped == 1
    service_type.return_value.generate_slots_for_series.assert_awaited_once_with(
        series_id=series.id, from_date=request.from_date,
        to_date=request.to_date, horizon_months=3,
    )
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_district_generation_enforces_scope_and_propagates_statistics() -> None:
    district = uuid.uuid4()
    repo, slots, db = AsyncMock(), AsyncMock(), AsyncMock()
    request = router.SlotGenerationRequest(horizon_months=2)

    with pytest.raises(HTTPException) as denied:
        await router.generate_slots_for_district(
            district, _auth(uuid.uuid4()), db, request,
            series_repo=repo, slot_repo=slots,
        )
    assert denied.value.status_code == 403
    db.commit.assert_not_awaited()

    with patch.object(router, "PlanningSeriesSlotGenerationService") as service_type:
        service_type.return_value.generate_slots_for_district = AsyncMock(
            return_value=_GENERATION
        )
        out = await router.generate_slots_for_district(
            district, _auth(district), db, request,
            series_repo=repo, slot_repo=slots,
        )
    assert out.districts_processed == 1
    service_type.return_value.generate_slots_for_district.assert_awaited_once_with(
        district_id=district, from_date=None, to_date=None, horizon_months=2,
    )
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_all_slots_requires_superadmin() -> None:
    repo, slots, db = AsyncMock(), AsyncMock(), AsyncMock()
    with pytest.raises(HTTPException) as denied:
        await router.generate_all_slots(
            _auth(uuid.uuid4()), db,
            series_repo=repo, slot_repo=slots,
        )
    assert denied.value.status_code == 403

    with patch.object(router, "PlanningSeriesSlotGenerationService") as service_type:
        service_type.return_value.generate_all_slots = AsyncMock(return_value=_GENERATION)
        out = await router.generate_all_slots(
            _auth(None, superadmin=True), db,
            series_repo=repo, slot_repo=slots,
        )
    assert out.generated == 2
    service_type.return_value.generate_all_slots.assert_awaited_once_with(
        from_date=None, to_date=None, horizon_months=6,
    )
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_exception_does_not_commit() -> None:
    district = uuid.uuid4()
    series = _series(district)
    repo, slots, db = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get.return_value = series
    with patch.object(router, "PlanningSeriesSlotGenerationService") as service_type:
        service_type.return_value.generate_slots_for_series = AsyncMock(
            side_effect=RuntimeError("temporary db failure")
        )
        with pytest.raises(RuntimeError, match="temporary db failure"):
            await router.generate_slots_for_series(
                series.id, _auth(district), db,
                series_repo=repo, slot_repo=slots,
            )
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("horizon", [0, 25])
def test_generation_request_rejects_out_of_bounds_horizon(horizon: int) -> None:
    with pytest.raises(ValidationError):
        router.SlotGenerationRequest(horizon_months=horizon)
