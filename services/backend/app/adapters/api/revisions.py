# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Strong validators shared by event, matrix and assignment writes."""

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot


def aware_timestamp(value: datetime) -> datetime:
    """Attach UTC to naive DB timestamps; preserve aware values and their precision."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def entity_revision(entity_id: object, updated_at: datetime) -> str:
    """Opaque strong ETag of a single-row entity: ``"<id>:<updated_at>"``.

    Equality-only, never parsed. Timestamps are ISO 8601 with timezone and six
    fractional digits, so two writes within one clock tick still differ once the
    caller advances ``updated_at`` with :func:`next_updated_at`.
    """
    return f'"{entity_id}:{aware_timestamp(updated_at).isoformat(timespec="microseconds")}"'


def content_revision(entity: object) -> str:
    """Strong ETag for rows without ``updated_at``: ``"<id>:<sha256 of the row content>"``.

    Equality-only like :func:`entity_revision`. Two states with identical content
    share a revision, which is harmless for a conditional write: the write would
    start from, and produce, the same content.
    """
    if not is_dataclass(entity) or isinstance(entity, type):
        raise TypeError("content_revision needs a dataclass instance")
    payload = json.dumps(asdict(entity), sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f'"{entity.id}:{digest}"'


def require_current_revision(if_match: str | None, current: str) -> None:
    """428 without a precondition, 412 if it no longer matches the stored revision."""
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match ist erforderlich.")
    if if_match != current:
        raise HTTPException(
            status_code=412, detail="Datensatz wurde zwischenzeitlich geändert."
        )


def next_updated_at(previous: datetime) -> datetime:
    """A strictly increasing timestamp, even for writes inside the same clock tick."""
    return max(datetime.now(UTC), aware_timestamp(previous) + timedelta(microseconds=1))


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
