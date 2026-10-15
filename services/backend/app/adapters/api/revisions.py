# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Strong validators shared by event, matrix and assignment writes."""

from datetime import UTC, datetime

from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot


def aware_timestamp(value: datetime) -> datetime:
    """Attach UTC to naive DB timestamps; preserve aware values and their precision."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def slot_revision(
    slot: PlanningSlot, instance: EventInstance | None = None
) -> str:
    """Opaque strong ETag for exact equality comparisons, never parsing.

    Wire format: one pair of double quotes around
    slot UUID : slot updated_at : instance updated_at (or the literal none).
    Timestamps use ISO 8601 including timezone and exactly six fractional
    digits. Colons also occur inside timestamps: neither clients nor server
    may split this representation or infer state from it.
    A change to either event model invalidates conditional writes.

    A slot without an instance uses the opaque "none" marker. Inserting its
    first instance invalidates that slot-only snapshot even if the slot did
    not change.
    """
    slot_updated = aware_timestamp(slot.updated_at).isoformat(timespec="microseconds")
    instance_updated = (
        aware_timestamp(instance.updated_at).isoformat(timespec="microseconds")
        if instance is not None else "none"
    )
    return f'"{slot.id}:{slot_updated}:{instance_updated}"'
