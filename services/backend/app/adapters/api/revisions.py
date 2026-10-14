# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Opaque strong revisions for planning-slot conditional mutations."""

from datetime import UTC

from app.domain.models.planning_slot import PlanningSlot


def slot_revision(slot: PlanningSlot) -> str:
    """Match the events API validator, normalizing naive DB timestamps as UTC."""
    updated_at = slot.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    return f'"{slot.id}:{updated_at.isoformat(timespec="microseconds")}"'
