# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Strong validators shared by event, matrix and assignment writes."""

from datetime import UTC, datetime

from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot


def _utc(value: datetime) -> datetime:
    """Treat naive DB timestamps as UTC, preserving microsecond precision."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def slot_revision(
    slot: PlanningSlot, instance: EventInstance | None = None
) -> str:
    """A change to either event model invalidates conditional writes."""
    slot_updated = _utc(slot.updated_at).isoformat(timespec="microseconds")
    instance_updated = (
        _utc(instance.updated_at).isoformat(timespec="microseconds")
        if instance is not None else "none"
    )
    return f'"{slot.id}:{slot_updated}:{instance_updated}"'
