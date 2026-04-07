from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class InvitationTargetType(str, Enum):
    DISTRICT_CONGREGATION = "DISTRICT_CONGREGATION"
    EXTERNAL_NOTE = "EXTERNAL_NOTE"


class OverwriteDecisionStatus(str, Enum):
    PENDING_OVERWRITE = "PENDING_OVERWRITE"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass
class CongregationInvitation:
    id: uuid.UUID
    source_event_id: uuid.UUID
    source_congregation_id: uuid.UUID
    target_type: InvitationTargetType
    target_congregation_id: uuid.UUID | None
    external_target_note: str | None
    linked_event_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        source_event_id: uuid.UUID,
        source_congregation_id: uuid.UUID,
        target_type: InvitationTargetType,
        target_congregation_id: uuid.UUID | None = None,
        external_target_note: str | None = None,
        linked_event_id: uuid.UUID | None = None,
    ) -> CongregationInvitation:
        if (
            target_type == InvitationTargetType.DISTRICT_CONGREGATION
            and target_congregation_id is None
        ):
            raise ValueError("target_congregation_id is required for DISTRICT_CONGREGATION")
        if target_type == InvitationTargetType.EXTERNAL_NOTE and not external_target_note:
            raise ValueError("external_target_note is required for EXTERNAL_NOTE")

        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            source_event_id=source_event_id,
            source_congregation_id=source_congregation_id,
            target_type=target_type,
            target_congregation_id=target_congregation_id,
            external_target_note=external_target_note,
            linked_event_id=linked_event_id,
            created_at=now,
            updated_at=now,
        )


@dataclass
class InvitationOverwriteRequest:
    id: uuid.UUID
    invitation_id: uuid.UUID
    source_event_id: uuid.UUID
    target_event_id: uuid.UUID
    proposed_title: str
    proposed_start_at: datetime
    proposed_end_at: datetime
    proposed_description: str | None
    proposed_category: str | None
    status: OverwriteDecisionStatus
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        invitation_id: uuid.UUID,
        source_event_id: uuid.UUID,
        target_event_id: uuid.UUID,
        proposed_title: str,
        proposed_start_at: datetime,
        proposed_end_at: datetime,
        proposed_description: str | None,
        proposed_category: str | None,
    ) -> InvitationOverwriteRequest:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            invitation_id=invitation_id,
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            proposed_title=proposed_title,
            proposed_start_at=proposed_start_at,
            proposed_end_at=proposed_end_at,
            proposed_description=proposed_description,
            proposed_category=proposed_category,
            status=OverwriteDecisionStatus.PENDING_OVERWRITE,
            decided_at=None,
            created_at=now,
            updated_at=now,
        )
