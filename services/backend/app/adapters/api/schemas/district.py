from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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


class CongregationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CongregationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
