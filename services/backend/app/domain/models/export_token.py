"""app/domain/models/export_token.py: Module."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, StrEnum


class TokenType(StrEnum):
    """TokenType domain model."""

    PUBLIC = "PUBLIC"  # leader names anonymized
    INTERNAL = "INTERNAL"  # full leader names visible


@dataclass
class ExportToken:
    id: uuid.UUID
    token: str
    label: str
    token_type: TokenType
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    leader_id: uuid.UUID | None
    created_at: datetime

    def confirmed_only(self, requested: str | None) -> bool:
        """Whether the ICS feed may contain only CONFIRMED slots (UC-05).

        PUBLIC tokens are shared outside the planning team, so they never expose
        PLANNED drafts, whatever the caller requests. INTERNAL tokens (including
        personal leader feeds) include drafts unless ``"confirmed_only"`` is
        requested.
        """
        return self.token_type == TokenType.PUBLIC or requested == "confirmed_only"

    @staticmethod
    def create(
        label: str,
        token_type: TokenType,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None,
        leader_id: uuid.UUID | None = None,
    ) -> ExportToken:
        return ExportToken(
            id=uuid.uuid4(),
            token=secrets.token_urlsafe(32),
            label=label,
            token_type=token_type,
            district_id=district_id,
            congregation_id=congregation_id,
            leader_id=leader_id,
            created_at=datetime.now(tz=UTC),
        )
