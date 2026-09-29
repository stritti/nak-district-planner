"""Field ownership and deterministic transitions for calendar synchronization."""

from __future__ import annotations

import logging
from enum import StrEnum

from app.domain.models.event_instance import SyncState

logger = logging.getLogger(__name__)


class SyncFieldAuthority(StrEnum):
    STRUCTURAL = "STRUCTURAL"
    SOFT = "SOFT"
    CONDITIONAL = "CONDITIONAL"


# Loop-prevention sentinel stored in ExternalEventLink.revision_marker after an
# internal deletion was pushed to the provider. Prevents re-import of the mapping.
INTERNAL_DELETE_MARKER = "internal:deleted"


FIELD_AUTHORITY = {
    **dict.fromkeys(
        ("id", "district_id", "series_id", "congregation_id", "category", "planning_date",
         "planning_time", "approval_status", "invitation_source_congregation_id",
         "invitation_source_event_id", "applicability", "planning_slot_id", "visibility",
         "created_at", "updated_at", "source", "sync_state", "external_uid", "content_hash",
         "calendar_integration_id", "last_external_modified_at", "last_internal_modified_at",
         "deviation_flag"),
        SyncFieldAuthority.STRUCTURAL,
    ),
    "title": SyncFieldAuthority.SOFT,
    "description": SyncFieldAuthority.SOFT,
    "actual_start_at": SyncFieldAuthority.CONDITIONAL,
    "actual_end_at": SyncFieldAuthority.CONDITIONAL,
    "status": SyncFieldAuthority.CONDITIONAL,
}


def classify_field(field: str) -> SyncFieldAuthority:
    if field not in FIELD_AUTHORITY:
        logger.warning("Unclassified calendar field %s; retaining internal authority", field)
    return FIELD_AUTHORITY.get(field, SyncFieldAuthority.STRUCTURAL)


def inbound_state(current: SyncState, *, changed: bool) -> SyncState:
    if not changed:
        return current
    if current in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
        return SyncState.CONFLICT
    return SyncState.DIRTY_EXTERNAL


def internal_state(current: SyncState) -> SyncState:
    if current in (SyncState.DIRTY_EXTERNAL, SyncState.CONFLICT):
        return SyncState.CONFLICT
    return SyncState.DIRTY_INTERNAL

