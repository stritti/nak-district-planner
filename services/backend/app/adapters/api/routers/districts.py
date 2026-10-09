"""app/adapters/api/routers/districts.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.api.deps import (
    CurrentUser,
    CurrentUserWithMemberships,
    DbSession,
    get_congregation_group_repository,
    get_congregation_repository,
    get_district_repository,
    get_event_instance_repository,
    get_invitation_repository,
    get_leader_repository,
    get_planning_series_repository,
    get_planning_slot_repository,
    get_service_assignment_repository,
)
from app.adapters.api.schemas.district import (
    CongregationCreate,
    CongregationGroupCreate,
    CongregationGroupResponse,
    CongregationGroupUpdate,
    CongregationResponse,
    CongregationUpdate,
    DistrictCreate,
    DistrictResponse,
    DistrictUpdate,
    FeiertageImportRequest,
    FeiertageImportResult,
    ServiceTime,
)
from app.adapters.api.schemas.matrix import MatrixCell, MatrixResponse, MatrixRow
from app.adapters.api.tenant_references import ensure_congregation_in_district
from app.adapters.auth.permissions import (
    PermissionError,
    assert_has_role_in_congregation,
    assert_has_role_in_district,
    get_districts_where_user_has_role,
    require_role_in_district,
    require_superadmin,
)
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.congregation_group import SqlCongregationGroupRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.invitation import SqlInvitationRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.planning_series import SqlPlanningSeriesRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.application.draft_service_generation import GenerateDraftServicesUseCase
from app.application.feiertage_service import (
    DE_STATES,
    import_feiertage,
    import_kirchliche_festtage,
    reference_feiertage_for_congregation,
)
from app.application.planning_series_generator import PlanningSeriesGenerator
from app.domain.models.congregation import Congregation
from app.domain.models.congregation_group import CongregationGroup
from app.domain.models.district import District
from app.domain.models.event_instance import EventInstance
from app.domain.models.invitation import CongregationInvitation
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.role import Role
from app.domain.models.service_assignment import ServiceAssignment

router = APIRouter(prefix="/api/v1/districts", tags=["districts"])


def _expected_dates(service_times: list[dict], from_date: date, to_date: date) -> list[str]:
    """Return ISO date strings for all expected Gottesdienst dates in [from_date, to_date]."""
    dates: list[str] = []
    seen: set[str] = set()
    current = from_date
    while current <= to_date:
        for st in service_times:
            if current.weekday() == st["weekday"]:
                iso = current.isoformat()
                if iso not in seen:
                    dates.append(iso)
                    seen.add(iso)
                break
        current += timedelta(days=1)
    return dates


# ── Districts ─────────────────────────────────────────────────────────────────


@router.post("", response_model=DistrictResponse, status_code=status.HTTP_201_CREATED)
async def create_district(
    body: DistrictCreate,
    user: CurrentUser,
    db: DbSession,
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
) -> DistrictResponse:
    require_superadmin(user, "Nur Superadmin darf Bezirke anlegen")

    state_code = body.state_code.upper() if body.state_code else None
    if state_code and state_code not in DE_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unbekanntes Bundesland-Kürzel: {state_code}. Gültig: {', '.join(DE_STATES)}",
        )

    district = District.create(name=body.name, state_code=state_code)
    await district_repo.save(district)

    year = datetime.now(UTC).year
    if district.state_code:
        try:
            await import_feiertage(
                district_id=district.id,
                year=year,
                state_code=district.state_code,
                session=db,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Feiertags-API nicht erreichbar: {exc}",
            ) from exc
    await import_kirchliche_festtage(
        district_id=district.id,
        year=year,
        session=db,
    )

    return _district_response(district)


@router.get("", response_model=list[DistrictResponse])
async def list_districts(
    auth: CurrentUserWithMemberships,
    db: DbSession,
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
) -> list[DistrictResponse]:
    districts = await district_repo.list_all()
    if not auth.user.is_superadmin:
        allowed_district_ids = set(get_districts_where_user_has_role(auth, Role.VIEWER))
        districts = [district for district in districts if district.id in allowed_district_ids]
    return [_district_response(d) for d in districts]


@router.patch("/{district_id}", response_model=DistrictResponse)
async def update_district(
    district_id: uuid.UUID,
    body: DistrictUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    repo: SqlDistrictRepository = Depends(get_district_repository),
) -> DistrictResponse:
    district = await repo.get(district_id)
    if not district:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        district.name = body.name
    if "state_code" in fields:
        district.state_code = body.state_code
    district.updated_at = datetime.now(UTC)
    await repo.save(district)
    return _district_response(district)


def _district_response(d: District) -> DistrictResponse:
    return DistrictResponse(
        id=d.id,
        name=d.name,
        state_code=d.state_code,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


# ── Congregations ─────────────────────────────────────────────────────────────


@router.post(
    "/{district_id}/congregations",
    response_model=CongregationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_congregation(
    district_id: uuid.UUID,
    body: CongregationCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> CongregationResponse:
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    await _validate_group_assignment(group_repo, district_id, body.group_id)
    await ensure_congregation_in_district(
        db, district_id, body.invitation_target_congregation_id,
        field="invitation_target_congregation_id",
    )
    service_times = (
        [st.model_dump() for st in body.service_times] if body.service_times is not None else None
    )
    congregation = Congregation.create(
        name=body.name,
        district_id=district_id,
        service_times=service_times,
        group_id=body.group_id,
        invitation_target_type=body.invitation_target_type,
        invitation_target_congregation_id=body.invitation_target_congregation_id,
        invitation_external_note=body.invitation_external_note,
    )
    await cong_repo.save(congregation)
    await reference_feiertage_for_congregation(
        district_id=district_id,
        congregation_id=congregation.id,
        session=db,
    )
    group_name = None
    if congregation.group_id is not None:
        group = await group_repo.get(congregation.group_id)
        group_name = group.name if group and group.district_id == district_id else None
    return _cong_response(congregation, group_name=group_name)


@router.get("/{district_id}/congregations", response_model=list[CongregationResponse])
async def list_congregations(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    group_id: uuid.UUID | None = Query(None),
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> list[CongregationResponse]:
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.VIEWER, district_id)
    congregations = await cong_repo.list_by_district(
        district_id, group_id=group_id
    )
    groups = await group_repo.list_by_district(district_id)
    group_names = {group.id: group.name for group in groups}
    return [
        _cong_response(c, group_name=group_names.get(c.group_id) if c.group_id else None)
        for c in congregations
    ]


@router.patch("/{district_id}/congregations/{congregation_id}", response_model=CongregationResponse)
async def update_congregation(
    district_id: uuid.UUID,
    congregation_id: uuid.UUID,
    body: CongregationUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> CongregationResponse:
    congregation = await cong_repo.get(congregation_id)
    if not congregation or congregation.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gemeinde nicht gefunden")
    # Determine if request comes through congregation_admin fallback
    is_congregation_scoped = False
    try:
        assert_has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    except PermissionError:
        try:
            assert_has_role_in_congregation(auth, Role.CONGREGATION_ADMIN, congregation_id)
            is_congregation_scoped = True
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    if body.name is not None:
        congregation.name = body.name
    if body.service_times is not None:
        congregation.service_times = [st.model_dump() for st in body.service_times]
    if "group_id" in body.model_fields_set:
        if is_congregation_scoped:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nur DISTRICT_ADMIN darf die Gruppenzugehörigkeit ändern",
            )
        await _validate_group_assignment(group_repo, district_id, body.group_id)
        congregation.group_id = body.group_id
    if "invitation_target_type" in body.model_fields_set:
        congregation.invitation_target_type = body.invitation_target_type
    if "invitation_target_congregation_id" in body.model_fields_set:
        await ensure_congregation_in_district(
            db, district_id, body.invitation_target_congregation_id,
            field="invitation_target_congregation_id",
        )
        congregation.invitation_target_congregation_id = body.invitation_target_congregation_id
    if "invitation_external_note" in body.model_fields_set:
        congregation.invitation_external_note = body.invitation_external_note
    congregation.updated_at = datetime.now(UTC)
    await cong_repo.save(congregation)
    group_name = None
    if congregation.group_id is not None:
        group = await group_repo.get(congregation.group_id)
        group_name = group.name if group and group.district_id == district_id else None
    return _cong_response(congregation, group_name=group_name)


async def _validate_group_assignment(
    group_repo: SqlCongregationGroupRepository,
    district_id: uuid.UUID,
    group_id: uuid.UUID | None,
) -> None:
    if group_id is None:
        return
    group = await group_repo.get(group_id)
    if group is None or group.district_id != district_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Gruppe ist ungueltig oder gehoert nicht zum Bezirk",
        )


def _cong_response(c: Congregation, group_name: str | None = None) -> CongregationResponse:
    return CongregationResponse(
        id=c.id,
        name=c.name,
        district_id=c.district_id,
        group_id=c.group_id,
        group_name=group_name,
        invitation_target_type=c.invitation_target_type,
        invitation_target_congregation_id=c.invitation_target_congregation_id,
        invitation_external_note=c.invitation_external_note,
        service_times=[ServiceTime(**st) for st in c.service_times],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── Congregation Groups ───────────────────────────────────────────────────────


@router.post(
    "/{district_id}/groups",
    response_model=CongregationGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    district_id: uuid.UUID,
    body: CongregationGroupCreate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> CongregationGroupResponse:
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    group = CongregationGroup.create(name=body.name, district_id=district_id)
    await group_repo.save(group)
    return _group_response(group)


@router.get("/{district_id}/groups", response_model=list[CongregationGroupResponse])
async def list_groups(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> list[CongregationGroupResponse]:
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.VIEWER, district_id)
    groups = await group_repo.list_by_district(district_id)
    return [_group_response(g) for g in groups]


@router.patch("/{district_id}/groups/{group_id}", response_model=CongregationGroupResponse)
async def update_group(
    district_id: uuid.UUID,
    group_id: uuid.UUID,
    body: CongregationGroupUpdate,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> CongregationGroupResponse:
    group = await group_repo.get(group_id)
    if not group or group.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gruppe nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    if body.name is not None:
        group.name = body.name
    group.updated_at = datetime.now(UTC)
    await group_repo.save(group)
    return _group_response(group)


@router.delete("/{district_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    district_id: uuid.UUID,
    group_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
) -> None:
    group = await group_repo.get(group_id)
    if not group or group.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gruppe nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    await group_repo.delete(group_id)


def _group_response(g: CongregationGroup) -> CongregationGroupResponse:
    return CongregationGroupResponse(
        id=g.id,
        name=g.name,
        district_id=g.district_id,
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


# ── Matrix ────────────────────────────────────────────────────────────────────


@router.get("/{district_id}/matrix", response_model=MatrixResponse)
async def get_matrix(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    group_id: uuid.UUID | None = Query(None),
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    cong_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    group_repo: SqlCongregationGroupRepository = Depends(get_congregation_group_repository),
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    leader_repo: SqlLeaderRepository = Depends(get_leader_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
    sa_repo: SqlServiceAssignmentRepository = Depends(get_service_assignment_repository),
    inv_repo: SqlInvitationRepository = Depends(get_invitation_repository),
) -> MatrixResponse:
    """Return matrix view for a district.

    Uses PlanningSlot as the authoritative source for all matrix cells.
    Holidays (Feiertag) are now stored as PlanningSlots with category="Feiertag".
    Event fallback has been removed as per OpenSpec requirement.

    **RBAC:** Requires VIEWER role in the district.
    """
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.VIEWER, district_id)

    def _ensure_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    utc_from_dt = _ensure_utc(from_dt) if from_dt is not None else None
    utc_to_dt = _ensure_utc(to_dt) if to_dt is not None else None

    if utc_from_dt is None and utc_to_dt is None:
        start_date = datetime.now(UTC).date()
        end_date = start_date + timedelta(days=27)
        effective_from_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        effective_to_dt = datetime.combine(end_date, time.max, tzinfo=UTC)
    elif utc_from_dt is None:
        assert utc_to_dt is not None  # guaranteed by first branch
        end_date = utc_to_dt.date()
        start_date = end_date - timedelta(days=27)
        effective_from_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        effective_to_dt = datetime.combine(end_date, time.max, tzinfo=UTC)
    elif utc_to_dt is None:
        assert utc_from_dt is not None  # guaranteed by first branch
        start_date = utc_from_dt.date()
        end_date = start_date + timedelta(days=27)
        effective_from_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        effective_to_dt = datetime.combine(end_date, time.max, tzinfo=UTC)
    else:
        effective_from_dt = utc_from_dt
        effective_to_dt = utc_to_dt

    if effective_to_dt < effective_from_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to_dt muss groesser oder gleich from_dt sein",
        )

    congregations = await cong_repo.list_by_district(
        district_id, group_id=group_id
    )
    from_date = effective_from_dt.date()
    to_date = effective_to_dt.date()

    # Compute expected Gottesdienst-Dates per congregation from their schedule
    expected_by_cong: dict[uuid.UUID, list[str]] = {
        c.id: _expected_dates(c.service_times, from_date, to_date) for c in congregations
    }

    # Load all ACTIVE PlanningSlots for the district in the date range (Gottesdienst
    # and Feiertag). CANCELLED slots are neither gaps nor services (issue #466).
    all_slots: list[PlanningSlot] = [
        slot
        for slot in await slot_repo.list_for_date_range(
            district_id=district_id,
            from_date=from_date,
            to_date=to_date,
        )
        if slot.status == PlanningSlotStatus.ACTIVE
    ]

    # Separate slots by category
    gottesdienst_slots: list[PlanningSlot] = [
        slot for slot in all_slots if slot.category == "Gottesdienst"
    ]
    feiertag_slots: list[PlanningSlot] = [slot for slot in all_slots if slot.category == "Feiertag"]

    # Build holidays dict from Feiertag PlanningSlots
    holidays: dict[str, list[str]] = {}
    for slot in feiertag_slots:
        date_key = slot.planning_date.isoformat()
        holidays.setdefault(date_key, []).append(slot.title or "Feiertag")

    # Collect all unique dates: congregation schedules + Feiertag dates + Gottesdienst slot dates
    all_dates: set[str] = set()
    for dates in expected_by_cong.values():
        all_dates.update(dates)
    all_dates.update(holidays.keys())  # kirchliche Feiertage immer als Spalten
    for slot in gottesdienst_slots:
        all_dates.add(slot.planning_date.isoformat())
    sorted_dates: list[str] = sorted(all_dates)

    gottesdienst_slots_by_date: dict[str, list[PlanningSlot]] = {}
    for slot in gottesdienst_slots:
        gottesdienst_slots_by_date.setdefault(slot.planning_date.isoformat(), []).append(slot)

    def _cell_slot(congregation_id: uuid.UUID, date_key: str) -> PlanningSlot | None:
        """Own slot before a distributed district slot; earliest time first."""
        visible = [
            slot
            for slot in gottesdienst_slots_by_date.get(date_key, [])
            if slot.is_visible_to(congregation_id)
        ]
        return min(
            visible,
            key=lambda slot: (slot.congregation_id is None, slot.planning_time),
            default=None,
        )

    # Batch-load leaders for this district
    leaders = await leader_repo.list_by_district(district_id)
    leaders_by_id = {leader.id: leader for leader in leaders}

    # Load EventInstances for all Gottesdienst slots
    instances: list[EventInstance] = await instance_repo.list_by_planning_slots(
        [slot.id for slot in gottesdienst_slots]
    )
    instance_by_slot_id: dict[uuid.UUID, EventInstance] = {
        instance.planning_slot_id: instance for instance in instances
    }

    # Load assignments for all Gottesdienst slots
    assignments: list[ServiceAssignment] = await sa_repo.list_by_planning_slots(
        [slot.id for slot in gottesdienst_slots]
    )
    assignment_by_slot_id: dict[uuid.UUID, ServiceAssignment] = {}
    for a in assignments:
        # `event_id` is kept as a temporary compatibility key for older assignment rows.
        assignment_key = a.planning_slot_id or a.event_id
        if assignment_key not in assignment_by_slot_id:
            assignment_by_slot_id[assignment_key] = a

    # Build matrix rows
    rows: list[MatrixRow] = []
    groups = await group_repo.list_by_district(district_id)
    group_names = {group.id: group.name for group in groups}
    congregation_name_by_id = {c.id: c.name for c in congregations}

    # Build source congregation names from slots with invitation_source_congregation_id
    source_congregation_ids: set[uuid.UUID] = {
        slot.invitation_source_congregation_id
        for slot in gottesdienst_slots
        if slot.invitation_source_congregation_id is not None
    }
    source_congregation_names: dict[uuid.UUID, str] = congregation_name_by_id.copy()
    if source_congregation_ids:
        source_congregations = await cong_repo.list_by_ids(
            list(source_congregation_ids)
        )
        for source in source_congregations:
            source_congregation_names[source.id] = source.name

    # Build invitation lookup: source_slot_id -> list of invitations
    # Use source_planning_slot_id if available, otherwise fall back to source_event_id
    source_slot_ids: list[uuid.UUID] = [
        slot.id for slot in gottesdienst_slots if slot.invitation_source_event_id is None
    ]
    invitations: list[CongregationInvitation] = await inv_repo.list_by_source_planning_slots(
        source_slot_ids
    )
    invitation_by_source_slot: dict[uuid.UUID, list[CongregationInvitation]] = {}
    for invitation in invitations:
        if invitation.source_planning_slot_id:
            invitation_by_source_slot.setdefault(invitation.source_planning_slot_id, []).append(
                invitation
            )

    # Names of invited congregations (they may lie outside the filtered group).
    missing_target_ids = {
        invitation.target_congregation_id
        for invitation in invitations
        if invitation.target_congregation_id is not None
        and invitation.target_congregation_id not in source_congregation_names
    }
    if missing_target_ids:
        for target in await cong_repo.list_by_ids(list(missing_target_ids)):
            source_congregation_names[target.id] = target.name

    def _invitation_target_labels(slot_id: uuid.UUID) -> list[str]:
        labels: list[str] = []
        for invitation in invitation_by_source_slot.get(slot_id, []):
            if invitation.target_congregation_id is not None:
                label = source_congregation_names.get(invitation.target_congregation_id)
            else:
                label = invitation.external_target_note
            if label and label not in labels:
                labels.append(label)
        return labels

    for congregation in congregations:
        cells: dict[str, MatrixCell] = {}

        for date_key in sorted_dates:
            slot: PlanningSlot | None = _cell_slot(congregation.id, date_key)

            if slot is None:
                # No visible slot for this congregation on this date
                cells[date_key] = MatrixCell()
                continue

            # Get instance and assignment for this slot
            instance: EventInstance | None = instance_by_slot_id.get(slot.id)
            assignment: ServiceAssignment | None = assignment_by_slot_id.get(slot.id)

            # Check if this is an invitation copy
            is_invitation_copy = slot.invitation_source_event_id is not None
            assignment_slot_id: uuid.UUID | None = slot.id

            # For invitation copies, try to get assignment from source
            if (
                assignment is None
                and is_invitation_copy
                and slot.invitation_source_event_id is not None
            ):
                assignment = assignment_by_slot_id.get(slot.invitation_source_event_id)
                if assignment is not None:
                    assignment_slot_id = slot.invitation_source_event_id

            # Resolve leader name from leader_id if leader_name is not set directly
            leader_name: str | None = None
            leader_id: uuid.UUID | None = None
            if assignment:
                leader_id = assignment.leader_id
                if assignment.leader_name:
                    leader_name = assignment.leader_name
                elif assignment.leader_id and assignment.leader_id in leaders_by_id:
                    ldr = leaders_by_id[assignment.leader_id]
                    rank_prefix = f"{ldr.rank.value} " if ldr.rank else ""
                    leader_name = f"{rank_prefix}{ldr.name}"

            # Get invitation count for this slot
            invitation_count: int = len(invitation_by_source_slot.get(slot.id, []))
            invitation_targets = _invitation_target_labels(slot.id)

            cells[date_key] = MatrixCell(
                event_id=slot.id,
                planning_slot_id=slot.id,
                assignment_event_id=assignment_slot_id,
                invitation_source_congregation_name=source_congregation_names.get(
                    slot.invitation_source_congregation_id
                )
                if slot.invitation_source_congregation_id is not None
                else None,
                event_title=instance.title if instance is not None else slot.title,
                event_start_at=(instance.actual_start_at if instance is not None else None),
                event_end_at=(instance.actual_end_at if instance is not None else None),
                category=slot.category,
                approval_status=slot.approval_status,
                # A service the congregation is invited away from needs no leader here.
                is_gap=(
                    assignment is None and not is_invitation_copy and invitation_count == 0
                ),
                planned_time=(
                    datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC)
                    if slot.planning_time is not None
                    else None
                ),
                actual_start_at=(instance.actual_start_at if instance is not None else None),
                actual_end_at=(instance.actual_end_at if instance is not None else None),
                has_deviation=instance.deviation_flag if instance is not None else False,
                is_assignment_editable=not is_invitation_copy,
                assignment_id=assignment.id if assignment else None,
                assignment_status=assignment.status if assignment else None,
                leader_id=leader_id,
                leader_name=leader_name,
                invitation_count=invitation_count,
                invitation_targets=invitation_targets,
                deviation_start_diff_minutes=None,
                deviation_end_diff_minutes=None,
            )

            # Calculate deviation details if instance exists and has deviation
            if instance is not None and instance.deviation_flag:
                from app.application.matrix_service import MatrixService

                start_diff, end_diff = MatrixService.calculate_deviation_minutes(slot, instance)
                cells[date_key].deviation_start_diff_minutes = start_diff
                cells[date_key].deviation_end_diff_minutes = end_diff

        rows.append(
            MatrixRow(
                congregation_id=congregation.id,
                congregation_name=congregation.name,
                group_id=congregation.group_id,
                group_name=group_names.get(congregation.group_id)
                if congregation.group_id
                else None,
                cells=cells,
            )
        )

    return MatrixResponse(dates=sorted_dates, rows=rows, holidays=holidays)


@router.post("/{district_id}/matrix/generate-drafts")
async def generate_matrix_drafts(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    congregation_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
) -> dict[str, int]:
    district = await district_repo.get(district_id)
    if not district:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")

    require_role_in_district(auth, Role.PLANNER, district_id)

    from_date = from_dt.date()
    to_date = to_dt.date()
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to_dt muss groesser oder gleich from_dt sein",
        )

    use_case = GenerateDraftServicesUseCase(
        district_repo=district_repo,
        congregation_repo=congregation_repo,
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )
    full_result = await use_case.run_for_window(
        from_date=from_date,
        to_date_exclusive=to_date + timedelta(days=1),
        district_ids={district_id},
    )
    await db.commit()

    return full_result


# ── PlanningSeries Auto-Generation ────────────────────────────────────────────


@router.post("/{district_id}/generate-planning-series")
async def generate_planning_series_slots(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
    congregation_repo: SqlCongregationRepository = Depends(get_congregation_repository),
    series_repo: SqlPlanningSeriesRepository = Depends(get_planning_series_repository),
    slot_repo: SqlPlanningSlotRepository = Depends(get_planning_slot_repository),
    instance_repo: SqlEventInstanceRepository = Depends(get_event_instance_repository),
) -> dict[str, int]:
    """Manually trigger PlanningSlot generation from active PlanningSeries."""
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)

    generator = PlanningSeriesGenerator(
        series_repo=series_repo,
        slot_repo=slot_repo,
        instance_repo=instance_repo,
        district_repo=district_repo,
        congregation_repo=congregation_repo,
    )
    result = await generator.run_for_window(
        from_date=from_dt.date(),
        to_date_exclusive=to_dt.date() + timedelta(days=1),
        district_ids={district_id},
    )
    await db.commit()
    return result


# ── Feiertage ─────────────────────────────────────────────────────────────────


@router.get("/{district_id}/feiertage/states")
async def list_de_states(_: CurrentUser) -> dict[str, str]:
    """Return mapping of 2-letter state codes to German names."""
    return DE_STATES


@router.post("/{district_id}/feiertage", response_model=FeiertageImportResult)
async def import_feiertage_endpoint(
    district_id: uuid.UUID,
    body: FeiertageImportRequest,
    auth: CurrentUserWithMemberships,
    db: DbSession,
    district_repo: SqlDistrictRepository = Depends(get_district_repository),
) -> FeiertageImportResult:
    """Import German public holidays from Nager.Date API into the district (idempotent)."""
    if not await district_repo.get(district_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)

    if body.state_code and body.state_code.upper() not in DE_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unbekanntes Bundesland-Kürzel: {body.state_code}. Gültig: {', '.join(DE_STATES)}",
        )

    totals = {"created": 0, "updated": 0, "skipped": 0}

    # 1. Gesetzliche Feiertage via Nager.Date (nur wenn Bundesland konfiguriert)
    if body.state_code:
        try:
            r = await import_feiertage(
                district_id=district_id,
                year=body.year,
                state_code=body.state_code.upper(),
                session=db,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Feiertags-API nicht erreichbar: {exc}",
            ) from exc
        for k in totals:
            totals[k] += r[k]

    # 2. Kirchliche Festtage (Palmsonntag, Ostersonntag, Pfingstsonntag) — immer
    r = await import_kirchliche_festtage(
        district_id=district_id,
        year=body.year,
        session=db,
    )
    for k in totals:
        totals[k] += r[k]

    return FeiertageImportResult(**totals)
