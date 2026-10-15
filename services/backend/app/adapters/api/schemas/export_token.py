# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/api/schemas/export_token.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.models.export_token import TokenType


class ExportTokenCreate(BaseModel):
    """ExportTokenCreate."""

    label: str = Field(min_length=1, max_length=200)
    token_type: TokenType
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None = None
    leader_id: uuid.UUID | None = None
    subject_sub: str | None = Field(default=None, min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_subject(self):
        if self.subject_sub is not None and (
            self.token_type != TokenType.INTERNAL or self.leader_id or self.congregation_id
        ):
            raise ValueError("Subject tokens require INTERNAL visibility and district scope")
        return self


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
    subject_sub: str | None = None
