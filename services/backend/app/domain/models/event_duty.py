# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Private organisational duties, independent of liturgical leadership."""

import unicodedata
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

DEFAULT_DUTY_CATEGORIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("closing", "Schließdienst", ()),
    ("organist", "Organist", ("Gottesdienst",)),
    ("conductor", "Dirigent", ("Gottesdienst",)),
)


def display_name(value: str) -> str:
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if not value or len(value) > 255 or any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("Invalid display name")
    return value


def normalize_name(value: str) -> str:
    return display_name(value).casefold()


@dataclass(frozen=True)
class EventDutyCategory:
    id: UUID
    district_id: UUID
    congregation_id: UUID | None
    code: str
    label: str
    event_categories: tuple[str, ...] = ()
    enabled: bool = True
    capacity: int = 1

    def __post_init__(self):
        """Validate positive capacity."""
        if self.capacity < 1:
            raise ValueError("Capacity must be positive")
        display_name(self.label)

    @classmethod
    def defaults(cls, district_id):
        return [
            cls(uuid4(), district_id, None, code, label, categories)
            for code, label, categories in DEFAULT_DUTY_CATEGORIES
        ]


@dataclass(frozen=True)
class EventTypeDutyConfiguration:
    id: UUID
    district_id: UUID
    congregation_id: UUID
    duty_category_id: UUID
    event_categories: tuple[str, ...]
    enabled: bool = True
    capacity: int = 1

    def __post_init__(self):
        """Validate positive capacity."""
        if self.capacity < 1:
            raise ValueError("Capacity must be positive")


def effective_categories(categories, overrides, event_category, congregation_id):
    result = []
    for category in categories:
        if category.congregation_id not in (None, congregation_id):
            continue
        override = next(
            (
                o
                for o in overrides
                if o.duty_category_id == category.id and o.congregation_id == congregation_id
            ),
            None,
        )
        effective = (
            replace(
                category,
                event_categories=override.event_categories,
                enabled=override.enabled,
                capacity=override.capacity,
            )
            if override
            else category
        )
        if effective.enabled and (
            not effective.event_categories or event_category in effective.event_categories
        ):
            result.append(effective)
    return result


@dataclass(frozen=True)
class EventDutyAssignment:
    id: UUID
    planning_slot_id: UUID
    duty_category_id: UUID
    district_id: UUID
    congregation_id: UUID | None
    display_name: str
    duty_label: str
    linked_user_sub: str | None
    normalized_name: str | None
    suggestion_id: UUID | None = None

    @classmethod
    def create(
        cls,
        slot_id,
        category,
        congregation_id,
        name=None,
        linked_user_sub=None,
        *,
        linked_display_name=None,
        suggestion_id=None,
    ):
        if bool(name) == bool(linked_user_sub):
            raise ValueError("Exactly one identity required")
        snapshot = display_name(linked_display_name if linked_user_sub else name)
        return cls(
            uuid4(),
            slot_id,
            category.id,
            category.district_id,
            congregation_id,
            snapshot,
            category.label,
            linked_user_sub,
            None if linked_user_sub else normalize_name(name),
            suggestion_id,
        )

    def visible_in(self, district_id, congregation_id):
        return self.district_id == district_id and self.congregation_id == congregation_id


@dataclass(frozen=True)
class DutyNameSuggestion:
    id: UUID
    district_id: UUID
    congregation_id: UUID | None
    duty_category_id: UUID
    display_name: str
    normalized_name: str
    hidden: bool = False
