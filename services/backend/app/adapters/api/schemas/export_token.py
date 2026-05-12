"""app/adapters/api/schemas/export_token.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.models.export_token import TokenType


class ExportTokenCreate(BaseModel):
    """ExportTokenCreate."""

    label: str
    token_type: TokenType
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None = None
    leader_id: uuid.UUID | None = None


class ExportTokenResponse(BaseModel):
    """ExportTokenResponse."""

    id: uuid.UUID
    token: str
    label: str
    token_type: TokenType
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    leader_id: uuid.UUID | None
    created_at: datetime
