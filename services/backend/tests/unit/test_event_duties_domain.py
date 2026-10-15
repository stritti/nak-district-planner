# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from uuid import uuid4

import pytest

from app.domain.models.event_duty import (
    EventDutyAssignment,
    EventDutyCategory,
    effective_categories,
    normalize_name,
)


def test_defaults_are_exact_and_overrides_win():
    d, c = uuid4(), uuid4()
    categories = EventDutyCategory.defaults(d)
    assert [x.label for x in effective_categories(categories, [], "Gottesdienst", c)] == [
        "Schließdienst",
        "Organist",
        "Dirigent",
    ]
    assert [x.label for x in effective_categories(categories, [], "gottesdienst", c)] == [
        "Schließdienst"
    ]


def test_normalization_and_invalid_identity():
    assert normalize_name(" Anna  Beispiel ") == "anna beispiel"
    with pytest.raises(ValueError):
        EventDutyAssignment.create(
            uuid4(), EventDutyCategory.defaults(uuid4())[0], None, "Anna", "sub"
        )


def test_original_scope_quarantines_after_move():
    d, c, other, slot = uuid4(), uuid4(), uuid4(), uuid4()
    assignment = EventDutyAssignment.create(slot, EventDutyCategory.defaults(d)[0], c, "Anna")
    assert assignment.visible_in(d, c)
    assert not assignment.visible_in(d, other)
