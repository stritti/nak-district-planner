from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class TokenType(str, Enum):
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
    created_at: datetime

    @staticmethod
    def create(
        label: str,
        token_type: TokenType,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None,
    ) -> "ExportToken":
        return ExportToken(
            id=uuid.uuid4(),
            token=secrets.token_urlsafe(32),
            label=label,
            token_type=token_type,
            district_id=district_id,
            congregation_id=congregation_id,
            created_at=datetime.now(tz=timezone.utc),
        )
