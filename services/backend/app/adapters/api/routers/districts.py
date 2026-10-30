# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/api/routers/districts.py: Module."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.adapters.api.deps import (
    CurrentUser,
    CurrentUserWithMemberships,
    DbSession,
    get_congregation_group_repository,
    get_congregation_repository,
    get_district_repository,
    get_event_duties_repository,
    get_event_instance_repository,
    get_invitation_repository,
    get_leader_repository,
    get_leader_unavailability_repository,
    get_planning_series_repository,
    get_planning_slot_repository,
    get_service_assignment_repository,
)
from app.adapters.api.matrix_builder import build_matrix
from app.adapters.api.revisions import (
    entity_revision,
    next_updated_at,
    require_current_revision,
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
from app.adapters.api.schemas.matrix import (
    MatrixResponse,
)
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
from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.invitation import SqlInvitationRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)
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
from app.domain.models.leader import normalize_leader_name
from app.domain.models.role import Role

router = APIRouter(prefix="/api/v1/districts", tags=["districts"])


def _reject_taken_name(name: str, others: Iterable[Any], what: str) -> None:
    """409 when another unit already uses the name (case-, space- and compatibility-insensitive).

    Enforced in the API only: duplicates that predate the rule stay untouched.
    """
    wanted = normalize_leader_name(name)
    if any(normalize_leader_name(other.name) == wanted for other in others):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"{what} mit diesem Namen existiert bereits"
        )


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unbekanntes Bundesland-Kürzel: {state_code}. Gültig: {', '.join(DE_STATES)}",
        )

    _reject_taken_name(body.name, await district_repo.list_all(), "Ein Bezirk")
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
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> DistrictResponse:
    district = await repo.get_for_update(district_id)
    if not district:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bezirk nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    require_current_revision(if_match, entity_revision(district.id, district.updated_at))
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        _reject_taken_name(
            body.name, [d for d in await repo.list_all() if d.id != district.id], "Ein Bezirk"
        )
        district.name = body.name
    if "state_code" in fields:
        district.state_code = body.state_code
    district.updated_at = next_updated_at(district.updated_at)
    await repo.save(district)
    return _district_response(district)


def _district_response(d: District) -> DistrictResponse:
    return DistrictResponse(
        id=d.id,
        name=d.name,
        state_code=d.state_code,
        created_at=d.created_at,
        updated_at=d.updated_at,
        revision=entity_revision(d.id, d.updated_at),
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
    _reject_taken_name(
        body.name, await cong_repo.list_by_district(district_id), "Eine Gemeinde"
    )
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
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> CongregationResponse:
    congregation = await cong_repo.get_for_update(congregation_id)
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
    require_current_revision(if_match, entity_revision(congregation.id, congregation.updated_at))
    if body.name is not None:
        if normalize_leader_name(body.name) != normalize_leader_name(congregation.name):
            _reject_taken_name(
                body.name,
                [c for c in await cong_repo.list_by_district(district_id) if c.id != congregation.id],
                "Eine Gemeinde",
            )
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
    congregation.updated_at = next_updated_at(congregation.updated_at)
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        revision=entity_revision(c.id, c.updated_at),
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
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> CongregationGroupResponse:
    group = await group_repo.get_for_update(group_id)
    if not group or group.district_id != district_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gruppe nicht gefunden")
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)
    require_current_revision(if_match, entity_revision(group.id, group.updated_at))
    if body.name is not None:
        group.name = body.name
    group.updated_at = next_updated_at(group.updated_at)
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
        revision=entity_revision(g.id, g.updated_at),
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
    duty_repo: SqlEventDutiesRepository = Depends(get_event_duties_repository),
    unavailability_repo: SqlLeaderUnavailabilityRepository = Depends(
        get_leader_unavailability_repository
    ),
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
    try:
        return await build_matrix(
            district_id,
            from_dt=from_dt,
            to_dt=to_dt,
            group_id=group_id,
            cong_repo=cong_repo,
            group_repo=group_repo,
            slot_repo=slot_repo,
            leader_repo=leader_repo,
            instance_repo=instance_repo,
            sa_repo=sa_repo,
            inv_repo=inv_repo,
            duty_repo=duty_repo,
            unavailability_repo=unavailability_repo,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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

    # 2. Kirchliche Festtage (berechnet) — immer
    r = await import_kirchliche_festtage(
        district_id=district_id,
        year=body.year,
        session=db,
    )
    for k in totals:
        totals[k] += r[k]

    return FeiertageImportResult(**totals)
