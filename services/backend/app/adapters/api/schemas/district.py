"""app/adapters/api/schemas/district.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.models.invitation import InvitationTargetType


class ServiceTime(BaseModel):
    """ServiceTime."""

    weekday: int = Field(ge=0, le=6)  # 0=Mo … 6=So
    time: str = Field(pattern=r"^\d{2}:\d{2}$")  # "HH:MM"


class DistrictCreate(BaseModel):
    """DistrictCreate."""

    name: str = Field(min_length=1, max_length=255)
    state_code: str | None = Field(None, min_length=2, max_length=2)


class DistrictUpdate(BaseModel):
    """DistrictUpdate."""

    name: str | None = Field(None, min_length=1, max_length=255)
    state_code: str | None = Field(None, min_length=2, max_length=2)


class DistrictResponse(BaseModel):
    """DistrictResponse."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    state_code: str | None
    created_at: datetime
    updated_at: datetime


class CongregationCreate(BaseModel):
    """CongregationCreate."""

    name: str = Field(min_length=1, max_length=255)
    service_times: list[ServiceTime] | None = None  # None → Defaults
    group_id: uuid.UUID | None = None
    invitation_target_type: InvitationTargetType | None = None
    invitation_target_congregation_id: uuid.UUID | None = None
    invitation_external_note: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_invitation_target(self) -> "CongregationCreate":
        if self.invitation_target_type is None:
            if (
                self.invitation_target_congregation_id is not None
                or self.invitation_external_note is not None
            ):
                raise ValueError(
                    "invitation_target_type is required when invitation target values are provided"
                )
            return self

        if self.invitation_target_type == InvitationTargetType.DISTRICT_CONGREGATION:
            if self.invitation_target_congregation_id is None:
                raise ValueError(
                    "invitation_target_congregation_id is required for DISTRICT_CONGREGATION"
                )
            if self.invitation_external_note is not None:
                raise ValueError("invitation_external_note must be empty for DISTRICT_CONGREGATION")
        elif self.invitation_target_type == InvitationTargetType.EXTERNAL_NOTE:
            if not self.invitation_external_note:
                raise ValueError("invitation_external_note is required for EXTERNAL_NOTE")
            if self.invitation_target_congregation_id is not None:
                raise ValueError(
                    "invitation_target_congregation_id must be empty for EXTERNAL_NOTE"
                )
        return self


class CongregationUpdate(BaseModel):
    """CongregationUpdate."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    service_times: list[ServiceTime] | None = None
    group_id: uuid.UUID | None = None
    invitation_target_type: InvitationTargetType | None = None
    invitation_target_congregation_id: uuid.UUID | None = None
    invitation_external_note: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_invitation_target(self) -> "CongregationUpdate":
        target_type_set = "invitation_target_type" in self.model_fields_set
        target_id_set = "invitation_target_congregation_id" in self.model_fields_set
        external_set = "invitation_external_note" in self.model_fields_set

        if not (target_type_set or target_id_set or external_set):
            return self

        if self.invitation_target_type is None:
            if target_id_set and self.invitation_target_congregation_id is not None:
                raise ValueError(
                    "invitation_target_type is required when invitation_target_congregation_id is set"
                )
            if external_set and self.invitation_external_note is not None:
                raise ValueError(
                    "invitation_target_type is required when invitation_external_note is set"
                )
            return self

        if self.invitation_target_type == InvitationTargetType.DISTRICT_CONGREGATION:
            if self.invitation_target_congregation_id is None:
                raise ValueError(
                    "invitation_target_congregation_id is required for DISTRICT_CONGREGATION"
                )
            if self.invitation_external_note is not None:
                raise ValueError("invitation_external_note must be empty for DISTRICT_CONGREGATION")
        elif self.invitation_target_type == InvitationTargetType.EXTERNAL_NOTE:
            if not self.invitation_external_note:
                raise ValueError("invitation_external_note is required for EXTERNAL_NOTE")
            if self.invitation_target_congregation_id is not None:
                raise ValueError(
                    "invitation_target_congregation_id must be empty for EXTERNAL_NOTE"
                )

        return self


class CongregationResponse(BaseModel):
    """CongregationResponse."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    group_id: uuid.UUID | None
    group_name: str | None = None
    invitation_target_type: InvitationTargetType | None
    invitation_target_congregation_id: uuid.UUID | None
    invitation_external_note: str | None
    service_times: list[ServiceTime]
    created_at: datetime
    updated_at: datetime


class CongregationGroupCreate(BaseModel):
    """CongregationGroupCreate."""

    name: str = Field(min_length=1, max_length=255)


class CongregationGroupUpdate(BaseModel):
    """CongregationGroupUpdate."""

    name: str | None = Field(default=None, min_length=1, max_length=255)


class CongregationGroupResponse(BaseModel):
    """CongregationGroupResponse."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class FeiertageImportRequest(BaseModel):
    """FeiertageImportRequest."""

    year: int = Field(..., ge=2020, le=2035)
    state_code: str | None = Field(
        None,
        min_length=2,
        max_length=2,
        description="2-Buchstaben Bundesland-Kürzel (z.B. BY, NW) oder leer für nur bundesweite Feiertage",
    )


class FeiertageImportResult(BaseModel):
    """FeiertageImportResult."""

    created: int
    updated: int
    skipped: int
