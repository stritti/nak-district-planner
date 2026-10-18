# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Planning conflicts between the assignments shown in one matrix (pure domain logic)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from app.domain.planning.conflict_result import ConflictContext, ConflictResult, ExistingAssignment
from app.domain.planning.conflict_rules import no_double_booking, travel_time_check
from app.domain.planning.conflict_service import ConflictService


@dataclass(frozen=True)
class PlannedService:
    """One leader assignment with the window of its event; ``key`` identifies the assignment."""

    key: uuid.UUID
    leader_id: uuid.UUID
    congregation_id: uuid.UUID | None
    start_time: datetime
    end_time: datetime


def matrix_conflicts(
    services: Iterable[PlannedService], *, min_travel_minutes: int
) -> dict[uuid.UUID, list[ConflictResult]]:
    """Conflicts per assignment key among the given assignments; conflict-free keys are omitted.

    Uses the same double-booking and travel-time rules as assigning a leader, so the
    matrix shows what the assignment dialog would object to if it were repeated now
    (for example after an event time changed).
    """
    by_leader: dict[uuid.UUID, list[PlannedService]] = defaultdict(list)
    for service in services:
        by_leader[service.leader_id].append(service)
    checker = ConflictService(rules=(no_double_booking, travel_time_check))
    result: dict[uuid.UUID, list[ConflictResult]] = {}
    for leader_id, planned in by_leader.items():
        for service in planned:
            context = ConflictContext(
                leader_id=leader_id,
                start_time=service.start_time,
                end_time=service.end_time,
                congregation_id=service.congregation_id,
                existing_assignments=tuple(
                    ExistingAssignment(leader_id, other.start_time, other.end_time, other.congregation_id)
                    for other in planned
                    if other.key != service.key
                ),
                min_travel_minutes=min_travel_minutes,
            )
            conflicts = checker.check(context)
            if conflicts:
                result[service.key] = conflicts
    return result
