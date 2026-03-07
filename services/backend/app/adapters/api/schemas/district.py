from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ServiceTime(BaseModel):
    weekday: int = Field(ge=0, le=6)  # 0=Mo … 6=So
    time: str = Field(pattern=r"^\d{2}:\d{2}$")  # "HH:MM"


class DistrictCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    state_code: str | None = Field(None, min_length=2, max_length=2)


class DistrictUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    state_code: str | None = Field(None, min_length=2, max_length=2)


class DistrictResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    state_code: str | None
    created_at: datetime
    updated_at: datetime


class CongregationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    service_times: list[ServiceTime] | None = None  # None → Defaults


class CongregationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    service_times: list[ServiceTime] | None = None


class CongregationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    service_times: list[ServiceTime]
    created_at: datetime
    updated_at: datetime


class FeiertageImportRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2035)
    state_code: str | None = Field(
        None,
        min_length=2,
        max_length=2,
        description="2-Buchstaben Bundesland-Kürzel (z.B. BY, NW) oder leer für nur bundesweite Feiertage",
    )


class FeiertageImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
