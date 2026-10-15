# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/domain/models/export_token.py: Module."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, StrEnum

TOKEN_HASH_PREFIX = "sha256"


def hash_export_token(token: str) -> str:
    """Return the storage form of an export token (prefixed SHA-256 hex)."""
    return f"{TOKEN_HASH_PREFIX}:{hashlib.sha256(token.encode('utf-8')).hexdigest()}"


def is_hashed_export_token(stored: str) -> bool:
    """Whether a stored token value is already in hashed form."""
    return stored.startswith(f"{TOKEN_HASH_PREFIX}:") and len(stored) == len(
        hash_export_token("")
    )


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

    subject_sub: str | None = None

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
        subject_sub: str | None = None,
    ) -> tuple[ExportToken, str]:
        if subject_sub is not None and (
            token_type != TokenType.INTERNAL or leader_id or congregation_id
        ):
            raise ValueError("Subject tokens require INTERNAL visibility and district scope")
        raw = secrets.token_urlsafe(32)
        return (
            ExportToken(
                id=uuid.uuid4(),
                token=hash_export_token(raw),
                label=label,
                token_type=token_type,
                district_id=district_id,
                congregation_id=congregation_id,
                leader_id=leader_id,
                created_at=datetime.now(tz=UTC),
                subject_sub=subject_sub,
            ),
            raw,
        )
