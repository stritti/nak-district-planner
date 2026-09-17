from __future__ import annotations

from app.domain.planning.conflict_result import ConflictContext, ConflictResult, Severity


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