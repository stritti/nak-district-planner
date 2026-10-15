# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Strong validators stay opaque and preserve timezone/microsecond semantics."""

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from app.adapters.api.revisions import aware_timestamp, slot_revision


def test_timezone_attachment_preserves_aware_values_and_microseconds():
    naive = datetime(2026, 10, 15, 10, 0, 0, 123456)
    assert aware_timestamp(naive) == naive.replace(tzinfo=UTC)
    aware = naive.replace(tzinfo=timezone(timedelta(hours=2)))
    assert aware_timestamp(aware) is aware


def test_validator_has_exact_quotes_precision_and_slot_only_marker():
    slot = SimpleNamespace(
        id=UUID(int=1), updated_at=datetime(2026, 10, 15, 10, 0, 0, 123456),
    )
    assert slot_revision(slot) == (
        '"00000000-0000-0000-0000-000000000001:2026-10-15T10:00:00.123456+00:00:none"'
    )
