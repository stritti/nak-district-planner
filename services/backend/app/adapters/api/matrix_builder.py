# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Assembly of the district service-assignment matrix (UC-03).

Extracted from the districts router so the HTTP layer keeps only
transport concerns (routing, RBAC, error mapping) while the matrix
aggregation lives in one testable module.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import NamedTuple

from app.adapters.api.revisions import slot_revision
from app.adapters.api.schemas.matrix import (
    MatrixCell,
    MatrixCellConflict,
    MatrixResponse,
    MatrixRow,
)
from app.config import settings
from app.domain.models.congregation import Congregation
from app.domain.models.event_instance import EventInstance
from app.domain.models.invitation import CongregationInvitation
from app.domain.models.leader import Leader, assignment_needs_review
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.service_assignment import ServiceAssignment
from app.domain.planning.conflict_result import ConflictResult, ScheduledService
from app.domain.planning.duty_conflicts import ScheduledDuty
from app.domain.planning.matrix_conflicts import PlannedService, matrix_conflicts
from app.domain.ports.event_duties import EventDutiesRepository
from app.domain.ports.repositories import (
    CongregationGroupRepository,
    CongregationRepository,
    EventInstanceRepository,
    InvitationRepository,
    LeaderRepository,
    LeaderUnavailabilityRepository,
    PlanningSlotRepository,
    ServiceAssignmentRepository,
)

# Placeholder for the duty lookup's excluded slot: no planning slot has the nil UUID.
_NO_SLOT = uuid.UUID(int=0)

# Default matrix window when the request gives no date bound: 28 days inclusive.
DEFAULT_WINDOW_DAYS = 28


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


def _planned_services(
    assignments: list[ServiceAssignment],
    slots: list[PlanningSlot],
    instance_by_slot_id: dict[uuid.UUID, EventInstance],
) -> list[PlannedService]:
    """Leader assignments of this matrix with the window of their event.

    Free-text guests carry no identity and are skipped; so are assignments whose slot
    lies outside the loaded range.
    """
    slot_by_id = {slot.id: slot for slot in slots}
    default_duration = timedelta(minutes=settings.sync_expected_duration_minutes)
    planned: list[PlannedService] = []
    for assignment in assignments:
        slot = slot_by_id.get(assignment.planning_slot_id or assignment.event_id)
        if assignment.leader_id is None or slot is None or slot.planning_time is None:
            continue
        instance = instance_by_slot_id.get(slot.id)
        start, end = ScheduledService(
            slot.congregation_id,
            slot.planning_date,
            slot.planning_time,
            instance.actual_start_at if instance else None,
            instance.actual_end_at if instance else None,
        ).window(default_duration)
        planned.append(
            PlannedService(
                assignment.id, assignment.leader_id, slot.congregation_id, start, end, slot.id
            )
        )
    return planned


async def _assignment_conflicts(
    district_id: uuid.UUID,
    planned: list[PlannedService],
    leaders_by_id: dict[uuid.UUID, Leader],
    *,
    duty_repo: EventDutiesRepository | None,
    unavailability_repo: LeaderUnavailabilityRepository | None,
) -> dict[uuid.UUID, list[ConflictResult]]:
    """Planning conflicts of the matrix assignments, as the assignment dialog checks them.

    Besides double booking and travel time among the loaded assignments, a leader's
    organisational duties, services outside the loaded matrix (another group, say)
    and recorded absences count. The duty lookup returns nothing for callers below
    PLANNER, and absences follow row-level security, so viewers see no more than
    they may read.
    """
    if not settings.conflict_check_enabled or not planned:
        return {}
    default_duration = timedelta(minutes=settings.sync_expected_duration_minutes)
    margin = default_duration + timedelta(minutes=settings.min_travel_minutes)
    window_start = min(service.start_time for service in planned) - margin
    window_end = max(service.end_time for service in planned) + margin
    leader_ids = sorted({service.leader_id for service in planned})

    other_bookings: dict[uuid.UUID, list[ScheduledDuty]] = {}
    if duty_repo is not None:
        for leader_id in leader_ids:
            leader = leaders_by_id.get(leader_id)
            other_bookings[leader_id] = await duty_repo.list_identity_schedule(
                district_id,
                linked_user_sub=leader.user_sub if leader else None,
                normalized_name=None,
                leader_id=leader_id,
                window_start=window_start,
                window_end=window_end,
                # The lookup compares slot ids with ``<>``, so it needs a value; the
                # matrix drops each assignment's own slot itself (matrix_conflicts).
                exclude_slot_id=_NO_SLOT,
            )

    absences: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}
    if unavailability_repo is not None:
        for item in await unavailability_repo.list_overlapping_for_leaders(
            leader_ids=leader_ids, start_at=window_start, end_at=window_end
        ):
            absences.setdefault(item.leader_id, []).append((item.start_at, item.end_at))

    return matrix_conflicts(
        planned,
        min_travel_minutes=settings.min_travel_minutes,
        other_bookings=other_bookings,
        unavailability=absences,
    )


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _resolve_window(
    from_dt: datetime | None,
    to_dt: datetime | None,
    *,
    default_days: int = DEFAULT_WINDOW_DAYS,
) -> tuple[datetime, datetime]:
    """Effective [from, to] window in UTC; a missing bound spans ``default_days``.

    Raises ValueError when both bounds are given and to_dt precedes from_dt.
    The comparison happens on the datetimes, before date normalization: two
    bounds on the same UTC day with inverted times are an invalid range even
    though their dates match (the router maps that to 422).
    """
    start = _ensure_utc(from_dt) if from_dt is not None else None
    end = _ensure_utc(to_dt) if to_dt is not None else None
    if start is not None and end is not None and end < start:
        raise ValueError("to_dt muss groesser oder gleich from_dt sein")
    span = timedelta(days=default_days - 1)
    start_date = start.date() if start is not None else None
    end_date = end.date() if end is not None else None
    if start_date is None:
        start_date = end_date - span if end_date is not None else datetime.now(UTC).date()
    if end_date is None:
        end_date = start_date + span
    effective_from_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
    effective_to_dt = datetime.combine(end_date, time.max, tzinfo=UTC)
    return effective_from_dt, effective_to_dt


class _MatrixRepos(NamedTuple):
    """The repositories the matrix assembly reads from."""

    cong_repo: CongregationRepository
    group_repo: CongregationGroupRepository
    slot_repo: PlanningSlotRepository
    leader_repo: LeaderRepository
    instance_repo: EventInstanceRepository
    sa_repo: ServiceAssignmentRepository
    inv_repo: InvitationRepository


class _MatrixData(NamedTuple):
    """Everything loaded once per matrix request, shared by the cell builders."""

    congregations: list[Congregation]
    group_names: dict[uuid.UUID, str]
    sorted_dates: list[str]
    holidays: dict[str, list[str]]
    gottesdienst_slots_by_date: dict[str, list[PlanningSlot]]
    leaders_by_id: dict[uuid.UUID, Leader]
    instance_by_slot_id: dict[uuid.UUID, EventInstance]
    assignment_by_slot_id: dict[uuid.UUID, ServiceAssignment]
    conflicts_by_assignment: dict[uuid.UUID, list[ConflictResult]]
    invitation_by_source_slot: dict[uuid.UUID, list[CongregationInvitation]]
    source_congregation_names: dict[uuid.UUID, str]


async def _load_matrix_data(
    district_id: uuid.UUID,
    group_id: uuid.UUID | None,
    from_date: date,
    to_date: date,
    repos: _MatrixRepos,
    *,
    duty_repo: EventDutiesRepository | None,
    unavailability_repo: LeaderUnavailabilityRepository | None,
) -> _MatrixData:
    congregations = await repos.cong_repo.list_by_district(district_id, group_id=group_id)
    expected_by_cong: dict[uuid.UUID, list[str]] = {
        c.id: _expected_dates(c.service_times, from_date, to_date) for c in congregations
    }

    # Load all ACTIVE PlanningSlots for the district in the date range (Gottesdienst
    # and Feiertag). CANCELLED slots are neither gaps nor services (issue #466).
    all_slots: list[PlanningSlot] = [
        slot
        for slot in await repos.slot_repo.list_for_date_range(
            district_id=district_id,
            from_date=from_date,
            to_date=to_date,
        )
        if slot.status == PlanningSlotStatus.ACTIVE
    ]
    gottesdienst_slots: list[PlanningSlot] = [
        slot for slot in all_slots if slot.category == "Gottesdienst"
    ]
    feiertag_slots: list[PlanningSlot] = [slot for slot in all_slots if slot.category == "Feiertag"]

    # Holidays (Feiertag) are slots too; they always appear as matrix columns.
    holidays: dict[str, list[str]] = {}
    for slot in feiertag_slots:
        holidays.setdefault(slot.planning_date.isoformat(), []).append(slot.title or "Feiertag")

    # Columns: congregation schedules + Feiertag dates + Gottesdienst slot dates.
    all_dates: set[str] = {d for dates in expected_by_cong.values() for d in dates}
    all_dates.update(holidays)
    all_dates.update(slot.planning_date.isoformat() for slot in gottesdienst_slots)
    sorted_dates: list[str] = sorted(all_dates)

    gottesdienst_slots_by_date: dict[str, list[PlanningSlot]] = {}
    for slot in gottesdienst_slots:
        gottesdienst_slots_by_date.setdefault(slot.planning_date.isoformat(), []).append(slot)

    leaders = await repos.leader_repo.list_by_district(district_id)
    leaders_by_id = {leader.id: leader for leader in leaders}

    instances: list[EventInstance] = await repos.instance_repo.list_by_planning_slots(
        [slot.id for slot in gottesdienst_slots]
    )
    instance_by_slot_id: dict[uuid.UUID, EventInstance] = {
        instance.planning_slot_id: instance for instance in instances
    }

    assignments: list[ServiceAssignment] = await repos.sa_repo.list_by_planning_slots(
        [slot.id for slot in gottesdienst_slots]
    )
    assignment_by_slot_id: dict[uuid.UUID, ServiceAssignment] = {}
    for assignment in assignments:
        # `event_id` is kept as a temporary compatibility key for older assignment rows.
        assignment_key = assignment.planning_slot_id or assignment.event_id
        if assignment_key not in assignment_by_slot_id:
            assignment_by_slot_id[assignment_key] = assignment

    conflicts_by_assignment = await _assignment_conflicts(
        district_id,
        _planned_services(assignments, gottesdienst_slots, instance_by_slot_id),
        leaders_by_id,
        duty_repo=duty_repo,
        unavailability_repo=unavailability_repo,
    )

    groups = await repos.group_repo.list_by_district(district_id)
    group_names = {group.id: group.name for group in groups}

    # Source congregation names for invitation copies.
    congregation_name_by_id = {c.id: c.name for c in congregations}
    source_congregation_ids: set[uuid.UUID] = {
        slot.invitation_source_congregation_id
        for slot in gottesdienst_slots
        if slot.invitation_source_congregation_id is not None
    }
    source_congregation_names: dict[uuid.UUID, str] = congregation_name_by_id.copy()
    if source_congregation_ids:
        for source in await repos.cong_repo.list_by_ids(list(source_congregation_ids)):
            source_congregation_names[source.id] = source.name

    # Invitation lookup: source_slot_id -> invitations.
    source_slot_ids: list[uuid.UUID] = [
        slot.id for slot in gottesdienst_slots if slot.invitation_source_event_id is None
    ]
    invitation_by_source_slot: dict[uuid.UUID, list[CongregationInvitation]] = {}
    for invitation in await repos.inv_repo.list_by_source_planning_slots(source_slot_ids):
        if invitation.source_planning_slot_id:
            invitation_by_source_slot.setdefault(
                invitation.source_planning_slot_id, []
            ).append(invitation)

    return _MatrixData(
        congregations=congregations,
        group_names=group_names,
        sorted_dates=sorted_dates,
        holidays=holidays,
        gottesdienst_slots_by_date=gottesdienst_slots_by_date,
        leaders_by_id=leaders_by_id,
        instance_by_slot_id=instance_by_slot_id,
        assignment_by_slot_id=assignment_by_slot_id,
        conflicts_by_assignment=conflicts_by_assignment,
        invitation_by_source_slot=invitation_by_source_slot,
        source_congregation_names=source_congregation_names,
    )


def _visible_cell_slots(data: _MatrixData, congregation_id: uuid.UUID, date_key: str) -> list[PlanningSlot]:
    """Visible services in display order, including later same-day services.

    The matrix currently presents one primary service per date. Keep the
    existing invitation precedence while retaining all visible services for
    conflict aggregation.
    """
    visible = [
        slot
        for slot in data.gottesdienst_slots_by_date.get(date_key, [])
        if slot.is_visible_to(congregation_id)
    ]
    copies = [s for s in visible if s.invitation_source_event_id is not None]
    if copies:
        led_own = [
            s
            for s in visible
            if s.invitation_source_event_id is None and s.id in data.assignment_by_slot_id
        ]
        visible = led_own or copies
    return sorted(
        visible,
        key=lambda slot: (slot.congregation_id is None, slot.planning_time),
    )


def _resolve_leader(
    assignment: ServiceAssignment | None,
    leaders_by_id: dict[uuid.UUID, Leader],
) -> tuple[uuid.UUID | None, str | None]:
    """Leader id and display name of an assignment (rank prefix for known leaders)."""
    if assignment is None:
        return None, None
    leader_id = assignment.leader_id
    if assignment.leader_name:
        return leader_id, assignment.leader_name
    if leader_id is not None and leader_id in leaders_by_id:
        leader = leaders_by_id[leader_id]
        rank_prefix = f"{leader.rank.value} " if leader.rank else ""
        return leader_id, f"{rank_prefix}{leader.name}"
    return leader_id, None


def _cell_conflicts(
    data: _MatrixData, visible_slots: list[PlanningSlot]
) -> list[MatrixCellConflict]:
    """Conflicts of every visible service in the cell, not only the primary one.

    The time prefix keeps the affected assignment identifiable when a day has
    more than one service, without changing the matrix shape.
    """
    conflicts: list[MatrixCellConflict] = []
    for visible_slot in visible_slots:
        visible_assignment = data.assignment_by_slot_id.get(visible_slot.id)
        if visible_assignment is None and visible_slot.invitation_source_event_id:
            visible_assignment = data.assignment_by_slot_id.get(
                visible_slot.invitation_source_event_id
            )
        if visible_assignment is None:
            continue
        for conflict in data.conflicts_by_assignment.get(visible_assignment.id, []):
            time_prefix = (
                f"{visible_slot.planning_time:%H:%M} Uhr: "
                if len(visible_slots) > 1 and visible_slot.planning_time is not None
                else ""
            )
            conflicts.append(
                MatrixCellConflict(
                    rule_id=conflict.rule_id,
                    severity=conflict.severity.value,
                    message=f"{time_prefix}{conflict.message}",
                )
            )
    return conflicts


def _build_cell(data: _MatrixData, congregation: Congregation, date_key: str) -> MatrixCell:
    visible_slots = _visible_cell_slots(data, congregation.id, date_key)
    if not visible_slots:
        # No visible slot for this congregation on this date
        return MatrixCell()
    slot = visible_slots[0]

    instance: EventInstance | None = data.instance_by_slot_id.get(slot.id)
    assignment: ServiceAssignment | None = data.assignment_by_slot_id.get(slot.id)

    # For invitation copies, fall back to the source slot's assignment.
    is_invitation_copy = slot.invitation_source_event_id is not None
    assignment_slot_id: uuid.UUID | None = slot.id
    if assignment is None and is_invitation_copy and slot.invitation_source_event_id is not None:
        assignment = data.assignment_by_slot_id.get(slot.invitation_source_event_id)
        if assignment is not None:
            assignment_slot_id = slot.invitation_source_event_id

    leader_id, leader_name = _resolve_leader(assignment, data.leaders_by_id)

    cell = MatrixCell(
        event_id=slot.id,
        planning_slot_id=slot.id,
        revision=slot_revision(slot, instance),
        assignment_event_id=assignment_slot_id,
        invitation_source_congregation_name=(
            data.source_congregation_names.get(slot.invitation_source_congregation_id)
            if slot.invitation_source_congregation_id is not None
            else None
        ),
        event_title=instance.title if instance is not None else slot.title,
        event_start_at=(instance.actual_start_at if instance is not None else None),
        event_end_at=(instance.actual_end_at if instance is not None else None),
        category=slot.category,
        approval_status=slot.approval_status,
        is_gap=(assignment is None and not is_invitation_copy),
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
        needs_review=assignment_needs_review(
            data.leaders_by_id.get(leader_id) if leader_id is not None else None,
            slot.planning_date,
        ),
        invitation_count=len(data.invitation_by_source_slot.get(slot.id, [])),
        service_count=len(visible_slots),
        deviation_start_diff_minutes=None,
        deviation_end_diff_minutes=None,
        conflicts=_cell_conflicts(data, visible_slots),
    )

    if instance is not None and instance.deviation_flag:
        from app.application.matrix_service import MatrixService

        start_diff, end_diff = MatrixService.calculate_deviation_minutes(slot, instance)
        cell.deviation_start_diff_minutes = start_diff
        cell.deviation_end_diff_minutes = end_diff

    return cell


async def build_matrix(
    district_id: uuid.UUID,
    *,
    from_dt: datetime | None,
    to_dt: datetime | None,
    group_id: uuid.UUID | None,
    cong_repo: CongregationRepository,
    group_repo: CongregationGroupRepository,
    slot_repo: PlanningSlotRepository,
    leader_repo: LeaderRepository,
    instance_repo: EventInstanceRepository,
    sa_repo: ServiceAssignmentRepository,
    inv_repo: InvitationRepository,
    duty_repo: EventDutiesRepository | None = None,
    unavailability_repo: LeaderUnavailabilityRepository | None = None,
) -> MatrixResponse:
    """Assemble the matrix response from repository data.

    Window defaults to 28 days when either bound is missing; ``to_dt``
    before ``from_dt`` is a validation error (422).
    """
    effective_from_dt, effective_to_dt = _resolve_window(from_dt, to_dt)
    repos = _MatrixRepos(
        cong_repo=cong_repo,
        group_repo=group_repo,
        slot_repo=slot_repo,
        leader_repo=leader_repo,
        instance_repo=instance_repo,
        sa_repo=sa_repo,
        inv_repo=inv_repo,
    )
    data = await _load_matrix_data(
        district_id,
        group_id,
        effective_from_dt.date(),
        effective_to_dt.date(),
        repos,
        duty_repo=duty_repo,
        unavailability_repo=unavailability_repo,
    )
    rows = [
        MatrixRow(
            congregation_id=congregation.id,
            congregation_name=congregation.name,
            group_id=congregation.group_id,
            group_name=data.group_names.get(congregation.group_id)
            if congregation.group_id
            else None,
            cells={date_key: _build_cell(data, congregation, date_key) for date_key in data.sorted_dates},
        )
        for congregation in data.congregations
    ]
    return MatrixResponse(dates=data.sorted_dates, rows=rows, holidays=data.holidays)
