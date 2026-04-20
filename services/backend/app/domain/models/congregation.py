"""app/domain/models/congregation.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.models.invitation import InvitationTargetType

# weekday: 0=Mo, 1=Di, 2=Mi, 3=Do, 4=Fr, 5=Sa, 6=So  (Python-Konvention)
DEFAULT_SERVICE_TIMES: list[dict] = [
    {"weekday": 6, "time": "09:30"},  # Sonntag
    {"weekday": 2, "time": "20:00"},  # Mittwoch
]


@dataclass
class Congregation:
    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    service_times: list[dict]
    created_at: datetime
    updated_at: datetime
    group_id: uuid.UUID | None = None
    invitation_target_type: InvitationTargetType | None = None
    invitation_target_congregation_id: uuid.UUID | None = None
    invitation_external_note: str | None = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        district_id: uuid.UUID,
        service_times: list[dict] | None = None,
        group_id: uuid.UUID | None = None,
        invitation_target_type: InvitationTargetType | None = None,
        invitation_target_congregation_id: uuid.UUID | None = None,
        invitation_external_note: str | None = None,
    ) -> Congregation:
        if invitation_target_type == InvitationTargetType.DISTRICT_CONGREGATION:
            if invitation_target_congregation_id is None:
                raise ValueError(
                    "invitation_target_congregation_id is required for DISTRICT_CONGREGATION"
                )
        if invitation_target_type == InvitationTargetType.EXTERNAL_NOTE:
            if not invitation_external_note:
                raise ValueError("invitation_external_note is required for EXTERNAL_NOTE")

        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            name=name,
            district_id=district_id,
            service_times=service_times
            if service_times is not None
            else list(DEFAULT_SERVICE_TIMES),
            created_at=now,
            updated_at=now,
            group_id=group_id,
            invitation_target_type=invitation_target_type,
            invitation_target_congregation_id=invitation_target_congregation_id,
            invitation_external_note=invitation_external_note,
        )
