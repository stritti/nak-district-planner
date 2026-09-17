from __future__ import annotations

from datetime import timedelta

from app.domain.planning.conflict_result import ConflictContext, ConflictResult, Severity

_LEADER_RANK_ORDER = (
    "Di.",
    "Pr.",
    "Ev.",
    "Hi.",
    "BE",
    "BÄ",
    "Bi.",
    "Ap.",
    "BezAp.",
    "StAp.",
)


def no_double_booking(context: ConflictContext) -> ConflictResult | None:
    """Block an assignment that overlaps another assignment for the same leader."""
    for assignment in context.existing_assignments:
        if assignment.leader_id != context.leader_id:
            continue
        if context.start_time < assignment.end_time and assignment.start_time < context.end_time:
            return ConflictResult(
                rule_id="no_double_booking",
                severity=Severity.BLOCK,
                message="Der Amtsträger ist in einem überlappenden Zeitraum bereits zugewiesen.",
                details={"existing_congregation_id": assignment.congregation_id},
            )
    return None


def travel_time_check(context: ConflictContext) -> ConflictResult | None:
    """Warn when different congregations leave too little travel time."""
    minimum_gap = timedelta(minutes=context.min_travel_minutes)
    for assignment in context.existing_assignments:
        if assignment.leader_id != context.leader_id:
            continue
        if assignment.congregation_id == context.congregation_id:
            continue
        if context.start_time >= assignment.end_time:
            gap = context.start_time - assignment.end_time
        elif assignment.start_time >= context.end_time:
            gap = assignment.start_time - context.end_time
        else:
            continue
        if gap < minimum_gap:
            return ConflictResult(
                rule_id="travel_time_check",
                severity=Severity.WARN,
                message="Die Wechselzeit zwischen Gemeinden ist zu kurz.",
                details={
                    "gap_minutes": int(gap.total_seconds() // 60),
                    "min_travel_minutes": context.min_travel_minutes,
                },
            )
    return None


def role_requirement_check(context: ConflictContext) -> ConflictResult | None:
    """Block an assignment when the leader rank is below the required rank."""
    if context.required_role is None:
        return None
    try:
        required_level = _LEADER_RANK_ORDER.index(context.required_role)
        leader_level = _LEADER_RANK_ORDER.index(context.leader_rank or "")
    except ValueError:
        leader_level = -1
        required_level = 0
    if leader_level >= required_level:
        return None
    return ConflictResult(
        rule_id="role_requirement_check",
        severity=Severity.BLOCK,
        message="Die Amtsstufe des Amtsträgers erfüllt die Dienstanforderung nicht.",
        details={
            "leader_rank": context.leader_rank,
            "required_role": context.required_role,
        },
    )


def leader_available(context: ConflictContext) -> ConflictResult | None:
    """Block an assignment that overlaps a leader unavailability period."""
    for unavailable_start, unavailable_end in context.unavailability_periods:
        if context.start_time < unavailable_end and unavailable_start < context.end_time:
            return ConflictResult(
                rule_id="leader_available",
                severity=Severity.BLOCK,
                message="Der Amtsträger ist im geplanten Zeitraum abwesend.",
                details={
                    "unavailable_start": unavailable_start,
                    "unavailable_end": unavailable_end,
                },
            )
    return None
