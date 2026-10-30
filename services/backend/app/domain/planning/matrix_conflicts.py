# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Planning conflicts between the assignments shown in one matrix (pure domain logic)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.domain.planning.conflict_result import ConflictContext, ConflictResult, ExistingAssignment
from app.domain.planning.conflict_rules import (
    leader_available,
    no_double_booking,
    travel_time_check,
)
from app.domain.planning.conflict_service import ConflictService
from app.domain.planning.duty_conflicts import ScheduledDuty


@dataclass(frozen=True)
class PlannedService:
    """One leader assignment with the window of its event; ``key`` identifies the assignment."""

    key: uuid.UUID
    leader_id: uuid.UUID
    congregation_id: uuid.UUID | None
    start_time: datetime
    end_time: datetime
    slot_id: uuid.UUID | None = None


def matrix_conflicts(
    services: Iterable[PlannedService],
    *,
    min_travel_minutes: int,
    other_bookings: Mapping[uuid.UUID, Sequence[ScheduledDuty]] | None = None,
    unavailability: Mapping[uuid.UUID, Sequence[tuple[datetime, datetime]]] | None = None,
) -> dict[uuid.UUID, list[ConflictResult]]:
    """Conflicts per assignment key among the given assignments; conflict-free keys are omitted.

    Uses the same double-booking, travel-time and availability rules as assigning a
    leader, so the matrix shows what the assignment dialog would object to if it were
    repeated now (for example after an event time changed or an absence was recorded).
    ``other_bookings`` holds further bookings per leader (organisational duties and
    services outside the loaded matrix); a booking on the assignment's own slot is
    ignored, as in the assignment dialog. ``unavailability`` holds absence periods
    per leader.
    """
    other_bookings = other_bookings or {}
    unavailability = unavailability or {}
    by_leader: dict[uuid.UUID, list[PlannedService]] = defaultdict(list)
    for service in services:
        by_leader[service.leader_id].append(service)
    checker = ConflictService(rules=(no_double_booking, travel_time_check, leader_available))
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
                )
                + tuple(
                    ExistingAssignment(leader_id, booking.start_time, booking.end_time, booking.congregation_id)
                    for booking in other_bookings.get(leader_id, ())
                    if service.slot_id is None or booking.slot_id != service.slot_id
                ),
                min_travel_minutes=min_travel_minutes,
                unavailability_periods=tuple(unavailability.get(leader_id, ())),
            )
            conflicts = checker.check(context)
            if conflicts:
                result[service.key] = conflicts
    return result
