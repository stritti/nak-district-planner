from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ServiceTime(BaseModel):
    weekday: int = Field(ge=0, le=6)  # 0=Mo … 6=So
    time: str = Field(pattern=r"^\d{2}:\d{2}$")  # "HH:MM"


class DistrictCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class DistrictUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class DistrictResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
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
