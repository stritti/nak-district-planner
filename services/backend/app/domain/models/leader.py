from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class LeaderRank(str, Enum):
    """Kirchliche Ränge in aufsteigender Reihenfolge."""

    DIAKON = "Di."
    PRIESTER = "Pr."
    EVANGELIST = "Ev."
    HIRTE = "Hi."
    BEZIRKSEVANGELIST = "BE"
    BEZIRKSAELTESTER = "BÄ"
    BISCHOF = "Bi."
    APOSTEL = "Ap."
    BEZIRKSAPOSTEL = "BezAp."
    STAMMAPOSTEL = "StAp."


class SpecialRole(str, Enum):
    """Besondere Beauftragung."""

    GEMEINDEVORSTEHER = "Gemeindevorsteher"
    BEZIRKSVORSTEHER = "Bezirksvorsteher"


@dataclass
class Leader:
    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    rank: LeaderRank | None
    special_role: SpecialRole | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        name: str,
        district_id: uuid.UUID,
        rank: LeaderRank | None = None,
        congregation_id: uuid.UUID | None = None,
        special_role: SpecialRole | None = None,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        is_active: bool = True,
    ) -> "Leader":
        now = datetime.now(timezone.utc)
        return Leader(
            id=uuid.uuid4(),
            name=name,
            district_id=district_id,
            congregation_id=congregation_id,
            rank=rank,
            special_role=special_role,
            email=email,
            phone=phone,
            notes=notes,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
