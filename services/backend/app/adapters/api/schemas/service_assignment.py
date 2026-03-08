import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.models.service_assignment import AssignmentStatus


class ServiceAssignmentCreate(BaseModel):
    leader_id: uuid.UUID | None = None
    leader_name: str | None = Field(default=None, min_length=1, max_length=255)
    status: AssignmentStatus = AssignmentStatus.ASSIGNED

    @model_validator(mode="after")
    def check_leader(self) -> "ServiceAssignmentCreate":
        if self.leader_id is None and not self.leader_name:
            raise ValueError("Entweder leader_id oder leader_name muss gesetzt sein")
        return self


class ServiceAssignmentUpdate(BaseModel):
    leader_id: uuid.UUID | None = None
    leader_name: str | None = Field(default=None, min_length=1, max_length=255)
    status: AssignmentStatus | None = None


class ServiceAssignmentResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    leader_id: uuid.UUID | None
    leader_name: str | None
    status: AssignmentStatus
    created_at: datetime
    updated_at: datetime
