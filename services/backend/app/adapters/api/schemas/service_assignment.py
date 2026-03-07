import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.service_assignment import AssignmentStatus


class ServiceAssignmentCreate(BaseModel):
    leader_name: str = Field(min_length=1, max_length=255)
    status: AssignmentStatus = AssignmentStatus.ASSIGNED


class ServiceAssignmentUpdate(BaseModel):
    leader_name: str | None = Field(default=None, min_length=1, max_length=255)
    status: AssignmentStatus | None = None


class ServiceAssignmentResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    leader_name: str
    status: AssignmentStatus
    created_at: datetime
    updated_at: datetime
