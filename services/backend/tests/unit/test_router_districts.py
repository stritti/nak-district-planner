from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, patch

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
from app.domain.models.congregation_group import CongregationGroup
from app.domain.models.district import District
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.invitation import CongregationInvitation, InvitationTargetType
from app.domain.models.leader import Leader, LeaderRank
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment


def _superadmin_user() -> object:
    return type("U", (), {"is_superadmin": True})()


def _superadmin_auth() -> object:
    return type(
        "A",
        (),
        {
            "user_sub": "superadmin",
            "memberships": [],
            "user": type("U", (), {"is_superadmin": True})(),
        },
    )()


def _matrix_repos(
    *,
    district: District | None,
    congregations: list | None = None,
    slots: list | None = None,
    instances: list | None = None,
    assignments: list | None = None,
    leaders: list | None = None,
    invitations: list | None = None,
) -> dict:
    district_repo = AsyncMock()
    district_repo.get.return_value = district

    cong_repo = AsyncMock()
    cong_repo.list_by_district.return_value = congregations or []
    cong_repo.list_by_ids.return_value = []

    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = slots or []

    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = instances or []

    sa_repo = AsyncMock()
    sa_repo.list_by_planning_slots.return_value = assignments or []

    leader_repo = AsyncMock()
    leader_repo.list_by_district.return_value = leaders or []

    group_repo = AsyncMock()
    group_repo.list_by_district.return_value = []

    inv_repo = AsyncMock()
    inv_repo.list_by_source_planning_slots.return_value = invitations or []

    return {
        "district_repo": district_repo,
        "cong_repo": cong_repo,
        "group_repo": group_repo,
        "slot_repo": slot_repo,
        "leader_repo": leader_repo,
        "instance_repo": instance_repo,
        "sa_repo": sa_repo,
        "inv_repo": inv_repo,
    }


@pytest.mark.asyncio
async def test_expected_dates_includes_matching_weekdays() -> None:
    from_date = datetime(2026, 4, 6, tzinfo=UTC).date()  # Monday
    to_date = from_date + timedelta(days=6)
    dates = r._expected_dates([{"weekday": 0, "time": "20:00"}], from_date, to_date)
    assert dates == ["2026-04-06"]


@pytest.mark.asyncio
async def test_create_district_rejects_unknown_state() -> None:
    with pytest.raises(HTTPException) as exc:
        await r.create_district(
            DistrictCreate(name="Bezirk", state_code="zz"), _superadmin_user(), AsyncMock()
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_district_handles_holiday_api_error() -> None:
    db = AsyncMock()
    district_repo = AsyncMock()
    with (
        patch(
            "app.adapters.api.routers.districts.import_feiertage",
            new=AsyncMock(side_effect=httpx.HTTPError("boom")),
        ),
        patch("app.adapters.api.routers.districts.import_kirchliche_festtage", new=AsyncMock()),
        pytest.raises(HTTPException) as exc,
    ):
        await r.create_district(
            DistrictCreate(name="Bezirk", state_code="BY"),
            _superadmin_user(),
            db,
            district_repo=district_repo,
        )
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_create_district_success() -> None:
    db = AsyncMock()
    district_repo = AsyncMock()
    with (
        patch(
            "app.adapters.api.routers.districts.import_feiertage", new=AsyncMock(return_value={})
        ) as import_feiertage,
        patch(
            "app.adapters.api.routers.districts.import_kirchliche_festtage",
            new=AsyncMock(return_value={}),
        ),
    ):
        out = await r.create_district(
            DistrictCreate(name="Bezirk", state_code="BY"),
            _superadmin_user(),
            db,
            district_repo=district_repo,
        )
    assert out.name == "Bezirk"
    assert out.state_code == "BY"
    assert import_feiertage.await_count == 1


@pytest.mark.asyncio
async def test_create_district_requires_superadmin() -> None:
    with pytest.raises(HTTPException) as exc:
        await r.create_district(
            DistrictCreate(name="Bezirk", state_code="BY"),
            object(),
            AsyncMock(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_district_not_found() -> None:
    repo = AsyncMock()
    repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await r.update_district(
            uuid.uuid4(), DistrictUpdate(name="X"), _superadmin_auth(), AsyncMock(), repo=repo
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_and_update_district_success() -> None:
    district_id = uuid.uuid4()
    district = District.create(name="Alt", state_code="BY")
    district.id = district_id

    repo = AsyncMock()
    repo.list_all.return_value = [district]
    repo.get.return_value = district

    listed = await r.list_districts(_superadmin_auth(), AsyncMock(), district_repo=repo)
    with (
        patch("app.adapters.api.routers.districts.assert_has_role_in_district"),
        patch("app.adapters.api.routers.districts.require_role_in_district"),
    ):
        updated = await r.update_district(
            district_id,
            DistrictUpdate(name="Neu", state_code="BW"),
            _superadmin_auth(),
            AsyncMock(),
            repo=repo,
        )

    assert len(listed) == 1
    assert listed[0].name == "Alt"
    assert updated.name == "Neu"
    assert updated.state_code == "BW"
    assert repo.save.await_count == 1


@pytest.mark.asyncio
async def test_list_districts_filters_for_non_superadmin() -> None:
    district_a = District.create(name="A", state_code="BY")
    district_b = District.create(name="B", state_code="BW")
    auth = type(
        "A",
        (),
        {
            "user_sub": "user-1",
            "memberships": [
                Membership.create(
                    user_sub="user-1",
                    role=Role.VIEWER,
                    scope_type=ScopeType.DISTRICT,
                    scope_id=district_a.id,
                )
            ],
            "user": type("U", (), {"is_superadmin": False})(),
        },
    )()

    repo = AsyncMock()
    repo.list_all.return_value = [district_a, district_b]

    listed = await r.list_districts(auth, AsyncMock(), district_repo=repo)

    assert len(listed) == 1
    assert listed[0].id == district_a.id


@pytest.mark.asyncio
async def test_create_and_list_congregations_success() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    cong = Congregation.create(name="Gemeinde A", district_id=district_id)
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="Bezirk")
    cong_repo = AsyncMock()
    cong_repo.list_by_district.return_value = [cong]
    group_repo = AsyncMock()
    group_repo.get.return_value = None

    with (
        patch("app.adapters.api.routers.districts.assert_has_role_in_district"),
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch(
            "app.adapters.api.routers.districts.reference_feiertage_for_congregation",
            new=AsyncMock(),
        ),
    ):
        created = await r.create_congregation(
            district_id,
            CongregationCreate(name="Gemeinde A"),
            object(),
            db,
            district_repo=district_repo,
            cong_repo=cong_repo,
            group_repo=group_repo,
        )
        listed = await r.list_congregations(
            district_id,
            _superadmin_auth(),
            db,
            district_repo=district_repo,
            cong_repo=cong_repo,
            group_repo=group_repo,
        )
    assert created.name == "Gemeinde A"
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_create_congregation_sets_group_name_when_group_matches_district() -> None:
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="Bezirk")
    cong_repo = AsyncMock()
    group = CongregationGroup.create(name="Nord", district_id=district_id)
    group.id = group_id
    group_repo = AsyncMock()
    group_repo.get.return_value = group

    with (
        patch("app.adapters.api.routers.districts.assert_has_role_in_district"),
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch(
            "app.adapters.api.routers.districts.reference_feiertage_for_congregation",
            new=AsyncMock(),
        ),
    ):
        created = await r.create_congregation(
            district_id,
            CongregationCreate(name="Gemeinde A", group_id=group_id),
            object(),
            db,
            district_repo=district_repo,
            cong_repo=cong_repo,
            group_repo=group_repo,
        )

    assert created.group_name == "Nord"


@pytest.mark.asyncio
async def test_update_congregation_updates_optional_fields_and_group_name() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="Alt", district_id=district_id)
    group_id = uuid.uuid4()

    cong_repo = AsyncMock()
    cong_repo.get.return_value = congregation

    group = CongregationGroup.create(name="Sued", district_id=district_id)
    group.id = group_id
    group_repo = AsyncMock()
    group_repo.get.return_value = group

    with (
        patch("app.adapters.api.routers.districts.assert_has_role_in_district"),
        patch("app.adapters.api.routers.districts.require_role_in_district"),
    ):
        updated = await r.update_congregation(
            district_id,
            congregation.id,
            CongregationUpdate(
                name="Neu",
                service_times=[{"weekday": 0, "time": "20:00"}],
                group_id=group_id,
                invitation_target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                invitation_target_congregation_id=uuid.uuid4(),
            ),
            object(),
            AsyncMock(),
            cong_repo=cong_repo,
            group_repo=group_repo,
        )
        await r.update_congregation(
            district_id,
            congregation.id,
            CongregationUpdate(
                invitation_target_type=InvitationTargetType.EXTERNAL_NOTE,
                invitation_external_note="Hinweis",
            ),
            object(),
            AsyncMock(),
            cong_repo=cong_repo,
            group_repo=group_repo,
        )

    assert updated.name == "Neu"
    assert updated.group_name == "Sued"
    assert updated.invitation_target_type == InvitationTargetType.DISTRICT_CONGREGATION
    assert cong_repo.save.await_count == 2


@pytest.mark.asyncio
async def test_validate_group_assignment_raises_on_cross_district() -> None:
    from unittest.mock import MagicMock

    district_id = uuid.uuid4()
    repo = MagicMock()
    repo.get = AsyncMock(return_value=MagicMock(district_id=uuid.uuid4()))
    with pytest.raises(HTTPException) as exc:
        await r._validate_group_assignment(repo, district_id, uuid.uuid4())
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_update_congregation_not_found() -> None:
    cong_repo = AsyncMock()
    cong_repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await r.update_congregation(
            uuid.uuid4(),
            uuid.uuid4(),
            CongregationUpdate(name="Neu"),
            object(),
            AsyncMock(),
            cong_repo=cong_repo,
            group_repo=AsyncMock(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_and_list_congregations_not_found_paths() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = None

    with pytest.raises(HTTPException) as create_exc:
        await r.create_congregation(
            district_id,
            CongregationCreate(name="G"),
            object(),
            db,
            district_repo=district_repo,
            cong_repo=AsyncMock(),
            group_repo=AsyncMock(),
        )
    with pytest.raises(HTTPException) as list_exc:
        await r.list_congregations(
            district_id,
            _superadmin_auth(),
            db,
            district_repo=district_repo,
            cong_repo=AsyncMock(),
            group_repo=AsyncMock(),
        )

    assert create_exc.value.status_code == 404
    assert list_exc.value.status_code == 404


@pytest.mark.asyncio
async def test_group_crud_success_paths() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")

    created_group = CongregationGroup.create(name="Nord", district_id=district_id)
    group_repo = AsyncMock()
    group_repo.list_by_district.return_value = [created_group]
    group_repo.get.return_value = created_group

    with (
        patch("app.adapters.api.routers.districts.assert_has_role_in_district"),
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch(
            "app.adapters.api.routers.districts.CongregationGroup.create",
            return_value=created_group,
        ),
    ):
        created = await r.create_group(
            district_id,
            r.CongregationGroupCreate(name="Nord"),
            object(),
            db,
            district_repo=district_repo,
            group_repo=group_repo,
        )
        listed = await r.list_groups(
            district_id, _superadmin_auth(), db, district_repo=district_repo, group_repo=group_repo
        )
        updated = await r.update_group(
            district_id,
            created_group.id,
            r.CongregationGroupUpdate(name="Nord-West"),
            object(),
            db,
            group_repo=group_repo,
        )
        await r.delete_group(district_id, created_group.id, object(), db, group_repo=group_repo)

    assert created.name == "Nord"
    assert len(listed) == 1
    assert updated.name == "Nord-West"
    assert group_repo.save.await_count >= 1
    assert group_repo.delete.await_count == 1


@pytest.mark.asyncio
async def test_group_crud_not_found_paths() -> None:
    district_id = uuid.uuid4()
    group_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await r.create_group(
            district_id,
            r.CongregationGroupCreate(name="G"),
            object(),
            db,
            district_repo=district_repo,
            group_repo=AsyncMock(),
        )
    with pytest.raises(HTTPException):
        await r.list_groups(
            district_id,
            _superadmin_auth(),
            db,
            district_repo=district_repo,
            group_repo=AsyncMock(),
        )

    district_repo.get.return_value = District.create(name="D")
    group_repo = AsyncMock()
    group_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await r.update_group(
            district_id,
            group_id,
            r.CongregationGroupUpdate(name="N"),
            object(),
            db,
            group_repo=group_repo,
        )
    with pytest.raises(HTTPException):
        await r.delete_group(district_id, group_id, object(), db, group_repo=group_repo)


@pytest.mark.asyncio
async def test_get_matrix_success() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)

    slot = PlanningSlot.create(
        district_id=district_id,
        congregation_id=congregation.id,
        planning_date=now.date(),
        planning_time=now.time(),
        category="Gottesdienst",
        title="Gottesdienst Mittwoch",
        status=PlanningSlotStatus.ACTIVE,
    )
    instance = EventInstance.create(
        planning_slot_id=slot.id,
        title="Gottesdienst Mittwoch",
        actual_start_at=now,
        actual_end_at=now + timedelta(hours=1),
        source=EventSource.INTERNAL,
        visibility=EventVisibility.INTERNAL,
    )
    assignment = ServiceAssignment.create(
        event_id=slot.id,
        planning_slot_id=slot.id,
        leader_name="Pr. Muster",
        status=AssignmentStatus.ASSIGNED,
    )
    repos = _matrix_repos(
        district=District.create(name="D"),
        congregations=[congregation],
        slots=[slot],
        instances=[instance],
        assignments=[assignment],
        leaders=[Leader.create(name="Muster", district_id=district_id)],
    )

    result = await r.get_matrix(
        district_id,
        _superadmin_auth(),
        AsyncMock(),
        from_dt=now - timedelta(days=2),
        to_dt=now + timedelta(days=2),
        group_id=None,
        **repos,
    )

    assert result.rows
    assert result.dates
    assert len(result.rows) == 1
    assert result.rows[0].congregation_id == congregation.id


@pytest.mark.asyncio
async def test_get_matrix_not_found_and_invalid_range() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()

    district_repo = AsyncMock()
    district_repo.get.return_value = None

    with pytest.raises(HTTPException) as not_found_exc:
        await r.get_matrix(
            district_id,
            _superadmin_auth(),
            db,
            from_dt=None,
            to_dt=None,
            group_id=None,
            district_repo=district_repo,
            cong_repo=AsyncMock(),
            group_repo=AsyncMock(),
            slot_repo=AsyncMock(),
            leader_repo=AsyncMock(),
            instance_repo=AsyncMock(),
            sa_repo=AsyncMock(),
            inv_repo=AsyncMock(),
        )
    assert not_found_exc.value.status_code == 404

    repos = _matrix_repos(district=District.create(name="D"))

    with pytest.raises(HTTPException) as range_exc:
        await r.get_matrix(
            district_id,
            _superadmin_auth(),
            db,
            from_dt=datetime(2030, 5, 2, tzinfo=UTC),
            to_dt=datetime(2030, 5, 1, tzinfo=UTC),
            group_id=None,
            **repos,
        )
    assert range_exc.value.status_code == 422


@pytest.mark.asyncio
async def test_get_matrix_handles_holidays_and_invitation_fallback_assignment() -> None:
    """Test matrix rendering with holidays (Feiertag PlanningSlots) and invitation fallback."""
    district_id = uuid.uuid4()
    congregation = Congregation.create(
        name="G",
        district_id=district_id,
        service_times=[{"weekday": 2, "time": "19:30"}],
    )
    source_congregation_id = uuid.uuid4()
    start = datetime(2030, 4, 10, 10, 0, tzinfo=UTC)
    start_date = start.date()

    source_slot = PlanningSlot.create(
        title="Gottesdienst Quelle",
        district_id=district_id,
        congregation_id=source_congregation_id,
        planning_date=start_date,
        planning_time=start.time(),
        category="Gottesdienst",
        status=PlanningSlotStatus.ACTIVE,
    )

    invite_copy_slot = PlanningSlot.create(
        title="Gottesdienst Ziel",
        district_id=district_id,
        congregation_id=congregation.id,
        planning_date=start_date,
        planning_time=start.time(),
        category="Gottesdienst",
        status=PlanningSlotStatus.ACTIVE,
        invitation_source_congregation_id=source_congregation_id,
        invitation_source_event_id=source_slot.id,
    )

    feiertag_date = start_date + timedelta(days=1)
    feiertag_slot = PlanningSlot.create(
        title="Karfreitag",
        district_id=district_id,
        congregation_id=None,
        planning_date=feiertag_date,
        planning_time=time(0, 0, 0),
        category="Feiertag",
        status=PlanningSlotStatus.ACTIVE,
    )

    leader = Leader.create(name="Muster", district_id=district_id, rank=LeaderRank.PRIESTER)
    assignment = ServiceAssignment.create(
        event_id=source_slot.id,
        planning_slot_id=source_slot.id,
        leader_id=leader.id,
        status=AssignmentStatus.ASSIGNED,
    )
    invitation = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_congregation_id,
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=congregation.id,
    )

    source_congregation = Congregation.create(name="Quelle", district_id=district_id)
    source_congregation.id = source_congregation_id

    repos = _matrix_repos(
        district=District.create(name="D"),
        congregations=[congregation],
        slots=[source_slot, invite_copy_slot, feiertag_slot],
        assignments=[assignment],
        leaders=[leader],
        invitations=[invitation],
    )
    repos["cong_repo"].list_by_ids.return_value = [source_congregation]

    result = await r.get_matrix(
        district_id,
        _superadmin_auth(),
        AsyncMock(),
        from_dt=start - timedelta(days=1),
        to_dt=start + timedelta(days=2),
        group_id=None,
        **repos,
    )

    assert result.holidays[feiertag_date.isoformat()] == ["Karfreitag"]

    cell = result.rows[0].cells[start_date.isoformat()]
    assert cell.assignment_event_id == source_slot.id
    assert cell.leader_name == f"{LeaderRank.PRIESTER.value} Muster"
    assert cell.is_assignment_editable is False
    assert cell.invitation_source_congregation_name == "Quelle"


@pytest.mark.asyncio
async def test_generate_matrix_drafts_error_paths() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    from_dt = datetime(2030, 4, 3, tzinfo=UTC)
    to_dt = datetime(2030, 4, 1, tzinfo=UTC)

    district_repo = AsyncMock()
    district_repo.get.return_value = None
    with pytest.raises(HTTPException) as not_found_exc:
        await r.generate_matrix_drafts(
            district_id,
            object(),
            db,
            from_dt=from_dt,
            to_dt=to_dt,
            district_repo=district_repo,
            congregation_repo=AsyncMock(),
            slot_repo=AsyncMock(),
            instance_repo=AsyncMock(),
        )
    assert not_found_exc.value.status_code == 404

    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    with patch(
        "app.adapters.api.routers.districts.require_role_in_district",
        side_effect=HTTPException(status_code=403),
    ):
        with pytest.raises(HTTPException) as forbidden_exc:
            await r.generate_matrix_drafts(
                district_id,
                object(),
                db,
                from_dt=from_dt,
                to_dt=to_dt,
                district_repo=district_repo,
                congregation_repo=AsyncMock(),
                slot_repo=AsyncMock(),
                instance_repo=AsyncMock(),
            )
    assert forbidden_exc.value.status_code == 403

    with patch("app.adapters.api.routers.districts.require_role_in_district"):
        with pytest.raises(HTTPException) as invalid_range_exc:
            await r.generate_matrix_drafts(
                district_id,
                object(),
                db,
                from_dt=from_dt,
                to_dt=to_dt,
                district_repo=district_repo,
                congregation_repo=AsyncMock(),
                slot_repo=AsyncMock(),
                instance_repo=AsyncMock(),
            )
    assert invalid_range_exc.value.status_code == 422


@pytest.mark.asyncio
async def test_get_matrix_defaults_to_4_weeks_when_range_missing() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    db = AsyncMock()

    repos = _matrix_repos(district=District.create(name="D"), congregations=[congregation])

    result = await r.get_matrix(
        district_id,
        _superadmin_auth(),
        db,
        from_dt=None,
        to_dt=None,
        group_id=None,
        **repos,
    )

    assert result.rows
    assert repos["slot_repo"].list_for_date_range.called
    call_args = repos["slot_repo"].list_for_date_range.await_args
    assert call_args.kwargs["from_date"] == datetime.now(UTC).date()
    assert call_args.kwargs["to_date"] == datetime.now(UTC).date() + timedelta(days=27)


@pytest.mark.asyncio
async def test_get_matrix_derives_from_dt_from_to_dt_when_missing() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    db = AsyncMock()
    to_dt = datetime(2025, 6, 15, 14, 30, tzinfo=UTC)

    repos = _matrix_repos(district=District.create(name="D"), congregations=[congregation])

    await r.get_matrix(
        district_id,
        _superadmin_auth(),
        db,
        from_dt=None,
        to_dt=to_dt,
        group_id=None,
        **repos,
    )

    assert repos["slot_repo"].list_for_date_range.called
    call_args = repos["slot_repo"].list_for_date_range.await_args
    expected_from_date = to_dt.date() - timedelta(days=27)
    assert call_args.kwargs["from_date"] == expected_from_date
    assert call_args.kwargs["to_date"] == to_dt.date()


@pytest.mark.asyncio
async def test_get_matrix_derives_to_dt_from_from_dt_when_missing() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    db = AsyncMock()

    repos = _matrix_repos(district=District.create(name="D"), congregations=[congregation])

    from_dt = datetime(2025, 7, 3, 9, 15, tzinfo=UTC)
    await r.get_matrix(
        district_id,
        _superadmin_auth(),
        db,
        from_dt=from_dt,
        to_dt=None,
        group_id=None,
        **repos,
    )

    assert repos["slot_repo"].list_for_date_range.called
    call_args = repos["slot_repo"].list_for_date_range.await_args
    expected_to_date = from_dt.date() + timedelta(days=27)
    assert call_args.kwargs["from_date"] == from_dt.date()
    assert call_args.kwargs["to_date"] == expected_to_date


@pytest.mark.asyncio
async def test_get_matrix_normalizes_naive_query_datetimes_to_utc() -> None:
    district_id = uuid.uuid4()
    congregation = Congregation.create(name="G", district_id=district_id)
    db = AsyncMock()

    repos = _matrix_repos(district=District.create(name="D"), congregations=[congregation])

    await r.get_matrix(
        district_id,
        _superadmin_auth(),
        db,
        from_dt=datetime(2030, 4, 1, 12, 0),
        to_dt=datetime(2030, 4, 15, 18, 45),
        group_id=None,
        **repos,
    )

    assert repos["slot_repo"].list_for_date_range.called
    call_args = repos["slot_repo"].list_for_date_range.await_args
    assert call_args.kwargs["from_date"] == date(2030, 4, 1)
    assert call_args.kwargs["to_date"] == date(2030, 4, 15)


@pytest.mark.asyncio
async def test_generate_matrix_drafts_success() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    now = datetime.now(UTC)
    congregation = Congregation.create(name="G", district_id=district_id)

    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")

    cong_repo = AsyncMock()
    cong_repo.list_by_district.return_value = [congregation]

    use_case = AsyncMock()
    use_case.run_for_window.return_value = {
        "districts": 1,
        "congregations": 1,
        "created": 1,
        "skipped_existing": 0,
        "adopted_existing": 0,
        "invalid_configurations": 0,
    }

    with (
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch(
            "app.adapters.api.routers.districts.GenerateDraftServicesUseCase",
            return_value=use_case,
        ),
    ):
        out = await r.generate_matrix_drafts(
            district_id,
            object(),
            db,
            from_dt=now - timedelta(days=1),
            to_dt=now + timedelta(days=1),
            district_repo=district_repo,
            congregation_repo=cong_repo,
            slot_repo=AsyncMock(),
            instance_repo=AsyncMock(),
        )
    assert out["created"] == 1


@pytest.mark.asyncio
async def test_list_de_states_returns_mapping() -> None:
    out = await r.list_de_states(object())
    assert out
    assert "BY" in out


@pytest.mark.asyncio
async def test_import_feiertage_endpoint_paths() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    with (
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch(
            "app.adapters.api.routers.districts.import_feiertage",
            new=AsyncMock(return_value={"created": 1, "updated": 0, "skipped": 0}),
        ),
        patch(
            "app.adapters.api.routers.districts.import_kirchliche_festtage",
            new=AsyncMock(return_value={"created": 1, "updated": 1, "skipped": 1}),
        ),
    ):
        out = await r.import_feiertage_endpoint(
            district_id,
            FeiertageImportRequest(year=2026, state_code="BY"),
            object(),
            db,
            district_repo=district_repo,
        )
    assert out.created == 2
    assert out.updated == 1
    assert out.skipped == 1


@pytest.mark.asyncio
async def test_import_feiertage_endpoint_invalid_state() -> None:
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    with patch("app.adapters.api.routers.districts.require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await r.import_feiertage_endpoint(
                uuid.uuid4(),
                FeiertageImportRequest(year=2026, state_code="ZZ"),
                object(),
                AsyncMock(),
                district_repo=district_repo,
            )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_import_feiertage_endpoint_not_found_and_http_error() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()

    district_repo = AsyncMock()
    district_repo.get.return_value = None

    with pytest.raises(HTTPException) as not_found_exc:
        await r.import_feiertage_endpoint(
            district_id,
            FeiertageImportRequest(year=2026, state_code="BY"),
            object(),
            db,
            district_repo=district_repo,
        )
    assert not_found_exc.value.status_code == 404

    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    with (
        patch("app.adapters.api.routers.districts.require_role_in_district"),
        patch(
            "app.adapters.api.routers.districts.import_feiertage",
            new=AsyncMock(side_effect=httpx.HTTPError("boom")),
        ),
    ):
        with pytest.raises(HTTPException) as api_exc:
            await r.import_feiertage_endpoint(
                district_id,
                FeiertageImportRequest(year=2026, state_code="BY"),
                object(),
                db,
                district_repo=district_repo,
            )
    assert api_exc.value.status_code == 502
