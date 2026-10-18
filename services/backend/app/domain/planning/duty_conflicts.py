# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Conflicts between organisational duties of one person (pure domain logic).

A person cannot hold two duties (organist, conductor, ...) at overlapping times,
neither in another congregation nor in the same one. A match through a verified
identity (linked account) blocks; a match through a typed name only warns, because
two people can share a name.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from app.domain.planning.conflict_result import ConflictResult, Severity


@dataclass(frozen=True)
class ScheduledDuty:
    """Another duty of the same person: its slot, congregation, window and match strength."""

    slot_id: uuid.UUID
    congregation_id: uuid.UUID | None
    start_time: datetime
    end_time: datetime
    strong: bool


def duty_identity_conflicts(
    start_time: datetime, end_time: datetime, others: Iterable[ScheduledDuty]
) -> list[ConflictResult]:
    """At most one BLOCK and one WARN result for the overlapping duties in ``others``."""
    overlapping = [
        other for other in others if start_time < other.end_time and other.start_time < end_time
    ]
    results: list[ConflictResult] = []
    strong = next((other for other in overlapping if other.strong), None)
    if strong is not None:
        results.append(
            ConflictResult(
                rule_id="duty_double_booking",
                severity=Severity.BLOCK,
                message="Dieselbe Person hat zur gleichen Zeit bereits einen Dienst.",
                details={"existing_congregation_id": strong.congregation_id},
            )
        )
    named = next((other for other in overlapping if not other.strong), None)
    if named is not None:
        results.append(
            ConflictResult(
                rule_id="duty_possible_namesake",
                severity=Severity.WARN,
                message="Ein Dienst mit gleichem Namen liegt zur gleichen Zeit vor – dieselbe Person?",
                details={"existing_congregation_id": named.congregation_id},
            )
        )
    return results
