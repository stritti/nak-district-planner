# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/domain/models/leader.py: Module."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum, StrEnum


class LeaderRank(StrEnum):
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


class SpecialRole(StrEnum):
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
    user_sub: str | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    hidden_from_lists: bool = False
    service_end_date: date | None = None

    def is_eligible_on(self, target_date: date) -> bool:
        return (
            self.is_active
            and not self.hidden_from_lists
            and (self.service_end_date is None or target_date <= self.service_end_date)
        )

    @staticmethod
    def create(
        name: str,
        district_id: uuid.UUID,
        rank: LeaderRank | None = None,
        congregation_id: uuid.UUID | None = None,
        special_role: SpecialRole | None = None,
        user_sub: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        is_active: bool = True,
        hidden_from_lists: bool = False,
        service_end_date: date | None = None,
    ) -> Leader:
        now = datetime.now(UTC)
        return Leader(
            id=uuid.uuid4(),
            name=name,
            district_id=district_id,
            congregation_id=congregation_id,
            rank=rank,
            special_role=special_role,
            user_sub=user_sub,
            email=email,
            phone=phone,
            notes=notes,
            is_active=is_active,
            hidden_from_lists=hidden_from_lists,
            service_end_date=service_end_date,
            created_at=now,
            updated_at=now,
        )


def normalize_leader_name(name: str) -> str:
    """Compare typed names without case, compatibility or whitespace bypasses."""
    import unicodedata

    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


_HONORIFICS = frozenset({"br", "bruder", "sr", "schwester", "dr", "prof", "herr", "frau"})


def _plain_tokens(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.findall(r"\w+", stripped.casefold())


def person_match_key(name: str) -> str:
    """Key under which two typed names count as the same person.

    Ignores case, spacing, punctuation, accents and leading honorifics or church
    ranks ("Br.", "Dr.", "Ev."). A match is only a hint that needs confirmation,
    never an identity: namesakes exist.
    """
    prefixes = _HONORIFICS | {t for rank in LeaderRank for t in _plain_tokens(rank.value)}
    tokens = _plain_tokens(name)
    while len(tokens) > 1 and tokens[0] in prefixes:
        tokens.pop(0)
    return " ".join(tokens)


def assignment_needs_review(
    leader: Leader | None, target_date: date, *, today: date | None = None
) -> bool:
    """Retain historical records; flag future appointments affected by lifecycle changes."""
    return bool(
        leader and target_date >= (today or date.today()) and not leader.is_eligible_on(target_date)
    )
