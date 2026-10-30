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

from app.adapters.api.revisions import slot_revision
from app.adapters.api.schemas.matrix import (
    MatrixCell,
    MatrixCellConflict,
    MatrixResponse,
    MatrixRow,
)
from app.config import settings
from app.domain.models.event_instance import EventInstance
from app.domain.models.invitation import CongregationInvitation
from app.domain.models.leader import Leader, assignment_needs_review
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.service_assignment import ServiceAssignment
from app.domain.planning.conflict_result import ConflictResult, ScheduledService
from app.domain.planning.duty_conflicts import ScheduledDuty
from app.domain.planning.matrix_conflicts import PlannedService, matrix_conflicts
from app.domain.ports.event_duties import EventDutiesRepository
from app.domain.ports.repositories import LeaderUnavailabilityRepository

# Placeholder for the duty lookup's excluded slot: no planning slot has the nil UUID.
_NO_SLOT = uuid.UUID(int=0)


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


async def build_matrix(
    district_id: uuid.UUID,
    *,
    from_dt: datetime | None,
    to_dt: datetime | None,
    group_id: uuid.UUID | None,
    cong_repo,
    group_repo,
    slot_repo,
    leader_repo,
    instance_repo,
    sa_repo,
    inv_repo,
    duty_repo: EventDutiesRepository | None = None,
    unavailability_repo: LeaderUnavailabilityRepository | None = None,
) -> MatrixResponse:
    """Assemble the matrix response from repository data.

    Window defaults to 28 days when either bound is missing; ``to_dt``
    before ``from_dt`` is a validation error (422).
    """

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
        raise ValueError("to_dt muss groesser oder gleich from_dt sein")

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

    def _visible_cell_slots(congregation_id: uuid.UUID, date_key: str) -> list[PlanningSlot]:
        """Visible services in display order, including later same-day services.

        The matrix currently presents one primary service per date. Keep the
        existing invitation precedence while retaining all visible services for
        conflict aggregation.
        """
        visible = [
            slot
            for slot in gottesdienst_slots_by_date.get(date_key, [])
            if slot.is_visible_to(congregation_id)
        ]
        copies = [s for s in visible if s.invitation_source_event_id is not None]
        if copies:
            led_own = [
                s
                for s in visible
                if s.invitation_source_event_id is None and s.id in assignment_by_slot_id
            ]
            visible = led_own or copies
        return sorted(
            visible,
            key=lambda slot: (slot.congregation_id is None, slot.planning_time),
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

    conflicts_by_assignment = await _assignment_conflicts(
        district_id,
        _planned_services(assignments, gottesdienst_slots, instance_by_slot_id),
        leaders_by_id,
        duty_repo=duty_repo,
        unavailability_repo=unavailability_repo,
    )

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

    for congregation in congregations:
        cells: dict[str, MatrixCell] = {}

        for date_key in sorted_dates:
            visible_slots = _visible_cell_slots(congregation.id, date_key)
            if not visible_slots:
                # No visible slot for this congregation on this date
                cells[date_key] = MatrixCell()
                continue
            slot = visible_slots[0]

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

            # The matrix has one cell per congregation and day. Include conflicts
            # from every visible service, not only the primary (earliest) one.
            # Prefix the time when there is more than one service so the affected
            # assignment remains identifiable without changing the matrix shape.
            cell_conflicts: list[MatrixCellConflict] = []
            for visible_slot in visible_slots:
                visible_assignment = assignment_by_slot_id.get(visible_slot.id)
                if visible_assignment is None and visible_slot.invitation_source_event_id:
                    visible_assignment = assignment_by_slot_id.get(
                        visible_slot.invitation_source_event_id
                    )
                if visible_assignment is None:
                    continue
                for conflict in conflicts_by_assignment.get(visible_assignment.id, []):
                    time_prefix = (
                        f"{visible_slot.planning_time:%H:%M} Uhr: "
                        if len(visible_slots) > 1 and visible_slot.planning_time is not None
                        else ""
                    )
                    cell_conflicts.append(
                        MatrixCellConflict(
                            rule_id=conflict.rule_id,
                            severity=conflict.severity.value,
                            message=f"{time_prefix}{conflict.message}",
                        )
                    )

            # Get invitation count for this slot
            invitation_count: int = len(invitation_by_source_slot.get(slot.id, []))

            cells[date_key] = MatrixCell(
                event_id=slot.id,
                planning_slot_id=slot.id,
                revision=slot_revision(slot, instance),
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
                    leaders_by_id.get(leader_id) if leader_id is not None else None,
                    slot.planning_date,
                ),
                invitation_count=invitation_count,
                service_count=len(visible_slots),
                deviation_start_diff_minutes=None,
                deviation_end_diff_minutes=None,
                conflicts=cell_conflicts,
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
