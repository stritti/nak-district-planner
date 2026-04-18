from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.adapters.api.routers import districts as r
from app.adapters.api.schemas.district import (
    CongregationCreate,
    CongregationUpdate,
    DistrictCreate,
    DistrictUpdate,
    FeiertageImportRequest,
)
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event import Event, EventStatus
from app.domain.models.leader import Leader
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment


@pytest.mark.asyncio
async def test_expected_dates_includes_matching_weekdays() -> None:
    from_date = datetime(2026, 4, 6, tzinfo=timezone.utc).date()  # Monday
    to_date = from_date + timedelta(days=6)
    dates = r._expected_dates([{"weekday": 0, "time": "20:00"}], from_date, to_date)
    assert dates == ["2026-04-06"]


@pytest.mark.asyncio
async def test_create_district_rejects_unknown_state() -> None:
    with pytest.raises(HTTPException) as exc:
        await r.create_district(
            DistrictCreate(name="Bezirk", state_code="zz"), object(), AsyncMock()
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_district_handles_holiday_api_error() -> None:
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as repo_cls,
        patch(
            "app.adapters.api.routers.districts.import_feiertage",
            new=AsyncMock(side_effect=httpx.HTTPError("boom")),
        ),
        patch("app.adapters.api.routers.districts.import_kirchliche_festtage", new=AsyncMock()),
    ):
        repo = AsyncMock()
        repo_cls.return_value = repo
        with pytest.raises(HTTPException) as exc:
            await r.create_district(DistrictCreate(name="Bezirk", state_code="BY"), object(), db)
        assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_create_district_success() -> None:
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as repo_cls,
        patch(
            "app.adapters.api.routers.districts.import_feiertage", new=AsyncMock(return_value={})
        ) as import_feiertage,
        patch(
            "app.adapters.api.routers.districts.import_kirchliche_festtage",
            new=AsyncMock(return_value={}),
        ),
    ):
        repo = AsyncMock()
        repo_cls.return_value = repo
        out = await r.create_district(DistrictCreate(name="Bezirk", state_code="BY"), object(), db)
    assert out.name == "Bezirk"
    assert out.state_code == "BY"
    assert import_feiertage.await_count == 1


@pytest.mark.asyncio
async def test_update_district_not_found() -> None:
    with patch("app.adapters.api.routers.districts.SqlDistrictRepository") as repo_cls:
        repo = AsyncMock()
        repo.get.return_value = None
        repo_cls.return_value = repo
        with pytest.raises(HTTPException) as exc:
            await r.update_district(uuid.uuid4(), DistrictUpdate(name="X"), object(), AsyncMock())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_and_list_congregations_success() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    cong = Congregation.create(name="Gemeinde A", district_id=district_id)
    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.districts.SqlCongregationRepository") as cong_repo_cls,
        patch(
            "app.adapters.api.routers.districts.SqlCongregationGroupRepository"
        ) as group_repo_cls,
        patch(
            "app.adapters.api.routers.districts.reference_feiertage_for_congregation",
            new=AsyncMock(),
        ),
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="Bezirk")
        district_repo_cls.return_value = district_repo
        cong_repo = AsyncMock()
        cong_repo.list_by_district.return_value = [cong]
        cong_repo_cls.return_value = cong_repo
        group_repo = AsyncMock()
        group_repo.list_by_district.return_value = []
        group_repo.get.return_value = None
        group_repo_cls.return_value = group_repo

        created = await r.create_congregation(
            district_id,
            CongregationCreate(name="Gemeinde A"),
            object(),
            db,
        )
        listed = await r.list_congregations(district_id, object(), db)
    assert created.name == "Gemeinde A"
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_validate_group_assignment_raises_on_cross_district() -> None:
    district_id = uuid.uuid4()
    wrong_group = MagicMock(district_id=uuid.uuid4())
    with patch("app.adapters.api.routers.districts.SqlCongregationGroupRepository") as repo_cls:
        repo = AsyncMock()
        repo.get.return_value = wrong_group
        repo_cls.return_value = repo
        with pytest.raises(HTTPException) as exc:
            await r._validate_group_assignment(AsyncMock(), district_id, uuid.uuid4())
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_update_congregation_not_found() -> None:
    with patch("app.adapters.api.routers.districts.SqlCongregationRepository") as repo_cls:
        repo = AsyncMock()
        repo.get.return_value = None
        repo_cls.return_value = repo
        with pytest.raises(HTTPException) as exc:
            await r.update_congregation(
                uuid.uuid4(),
                uuid.uuid4(),
                CongregationUpdate(name="Neu"),
                object(),
                AsyncMock(),
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_group_crud_not_found_paths() -> None:
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch(
            "app.adapters.api.routers.districts.SqlCongregationGroupRepository"
        ) as group_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = None
        district_repo_cls.return_value = district_repo
        with pytest.raises(HTTPException):
            await r.create_group(district_id, r.CongregationGroupCreate(name="G"), object(), db)
        with pytest.raises(HTTPException):
            await r.list_groups(district_id, object(), db)

        district_repo.get.return_value = District.create(name="D")
        group_repo = AsyncMock()
        group_repo.get.return_value = None
        group_repo_cls.return_value = group_repo
        with pytest.raises(HTTPException):
            await r.update_group(
                district_id, group_id, r.CongregationGroupUpdate(name="N"), object(), db
            )
        with pytest.raises(HTTPException):
            await r.delete_group(district_id, group_id, object(), db)


@pytest.mark.asyncio
async def test_get_matrix_success() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    now = datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc)
    event = Event.create(
        title="Gottesdienst Mittwoch",
        start_at=now,
        end_at=now + timedelta(hours=1),
        district_id=district_id,
        congregation_id=congregation.id,
        status=EventStatus.DRAFT,
        category="Gottesdienst",
    )
    assignment = ServiceAssignment.create(
        event_id=event.id,
        leader_name="Pr. Muster",
        status=AssignmentStatus.ASSIGNED,
    )
    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.districts.SqlCongregationRepository") as cong_repo_cls,
        patch("app.adapters.api.routers.districts.SqlEventRepository") as event_repo_cls,
        patch("app.adapters.api.routers.districts.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.districts.SqlLeaderRepository") as leader_repo_cls,
        patch(
            "app.adapters.api.routers.districts.SqlCongregationGroupRepository"
        ) as group_repo_cls,
        patch("app.adapters.api.routers.districts.SqlInvitationRepository") as inv_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        cong_repo = AsyncMock()
        cong_repo.list_by_district.return_value = [congregation]
        cong_repo.list_by_ids.return_value = []
        cong_repo_cls.return_value = cong_repo

        event_repo = AsyncMock()
        event_repo.list.return_value = ([event], 1)
        event_repo_cls.return_value = event_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_events.return_value = [assignment]
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = [
            Leader.create(name="Muster", district_id=district_id)
        ]
        leader_repo_cls.return_value = leader_repo

        group_repo = AsyncMock()
        group_repo.list_by_district.return_value = []
        group_repo_cls.return_value = group_repo

        inv_repo = AsyncMock()
        inv_repo.list_by_source_events.return_value = []
        inv_repo_cls.return_value = inv_repo

        result = await r.get_matrix(
            district_id,
            object(),
            AsyncMock(),
            from_dt=now - timedelta(days=2),
            to_dt=now + timedelta(days=2),
            group_id=None,
        )

    assert result.rows
    assert result.dates


@pytest.mark.asyncio
async def test_get_matrix_defaults_to_4_weeks_when_range_missing() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.districts.SqlCongregationRepository") as cong_repo_cls,
        patch("app.adapters.api.routers.districts.SqlEventRepository") as event_repo_cls,
        patch("app.adapters.api.routers.districts.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.districts.SqlLeaderRepository") as leader_repo_cls,
        patch(
            "app.adapters.api.routers.districts.SqlCongregationGroupRepository"
        ) as group_repo_cls,
        patch("app.adapters.api.routers.districts.SqlInvitationRepository") as inv_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        cong_repo = AsyncMock()
        cong_repo.list_by_district.return_value = [congregation]
        cong_repo.list_by_ids.return_value = []
        cong_repo_cls.return_value = cong_repo

        event_repo = AsyncMock()
        event_repo.list.return_value = ([], 0)
        event_repo_cls.return_value = event_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_events.return_value = []
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        group_repo = AsyncMock()
        group_repo.list_by_district.return_value = []
        group_repo_cls.return_value = group_repo

        inv_repo = AsyncMock()
        inv_repo.list_by_source_events.return_value = []
        inv_repo_cls.return_value = inv_repo

        result = await r.get_matrix(
            district_id,
            object(),
            db,
            from_dt=None,
            to_dt=None,
            group_id=None,
        )

    assert result.rows
    call_kwargs = event_repo.list.await_args.kwargs
    assert call_kwargs["to_dt"] > call_kwargs["from_dt"]
    assert call_kwargs["to_dt"] - call_kwargs["from_dt"] == timedelta(days=28)


@pytest.mark.asyncio
async def test_generate_matrix_drafts_success() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    now = datetime.now(timezone.utc)
    congregation = Congregation.create(name="G", district_id=district_id)
    event = Event.create(
        title="Gottesdienst",
        start_at=now,
        end_at=now + timedelta(hours=1),
        district_id=district_id,
        congregation_id=congregation.id,
        status=EventStatus.DRAFT,
        category="Gottesdienst",
        generation_slot_key="slot-1",
    )

    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.districts.assert_has_role_in_district"),
        patch("app.adapters.api.routers.districts.GenerateDraftServicesUseCase") as use_case_cls,
        patch("app.adapters.api.routers.districts.SqlCongregationRepository") as cong_repo_cls,
        patch("app.adapters.api.routers.districts.SqlEventRepository") as event_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        use_case = AsyncMock()
        use_case.run_for_window.return_value = {
            "districts": 1,
            "congregations": 1,
            "created": 1,
            "skipped_existing": 0,
            "adopted_existing": 0,
            "invalid_configurations": 0,
        }
        use_case_cls.return_value = use_case

        cong_repo = AsyncMock()
        cong_repo.list_by_district.return_value = [congregation]
        cong_repo_cls.return_value = cong_repo

        event_repo = AsyncMock()
        event_repo.list.return_value = ([event], 1)
        event_repo_cls.return_value = event_repo

        out = await r.generate_matrix_drafts(
            district_id,
            object(),
            db,
            from_dt=now - timedelta(days=1),
            to_dt=now + timedelta(days=1),
        )
    assert out["generated_in_requested_range"] == 1


@pytest.mark.asyncio
async def test_import_feiertage_endpoint_paths() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls,
        patch(
            "app.adapters.api.routers.districts.import_feiertage",
            new=AsyncMock(return_value={"created": 1, "updated": 0, "skipped": 0}),
        ),
        patch(
            "app.adapters.api.routers.districts.import_kirchliche_festtage",
            new=AsyncMock(return_value={"created": 1, "updated": 1, "skipped": 1}),
        ),
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo
        out = await r.import_feiertage_endpoint(
            district_id,
            FeiertageImportRequest(year=2026, state_code="BY"),
            object(),
            db,
        )
    assert out.created == 2
    assert out.updated == 1
    assert out.skipped == 1


@pytest.mark.asyncio
async def test_import_feiertage_endpoint_invalid_state() -> None:
    with patch("app.adapters.api.routers.districts.SqlDistrictRepository") as district_repo_cls:
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo
        with pytest.raises(HTTPException) as exc:
            await r.import_feiertage_endpoint(
                uuid.uuid4(),
                FeiertageImportRequest(year=2026, state_code="ZZ"),
                object(),
                AsyncMock(),
            )
    assert exc.value.status_code == 422
