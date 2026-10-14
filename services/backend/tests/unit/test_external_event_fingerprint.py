# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Canonical fingerprint tests, including previously missed cancellation changes."""

from datetime import UTC, datetime, timedelta

from app.domain.services.external_event_fingerprint import compute_content_hash


def test_fingerprint_deterministic_and_sensitive_to_sync_fields():
    start = datetime(2026, 10, 11, 8, tzinfo=UTC)
    end = start + timedelta(hours=1)
    original = compute_content_hash("uid", start, end, "Title", "Old", False)
    assert original == compute_content_hash("uid", start, end, "Title", "Old", False)
    assert original != compute_content_hash("uid", start, end, "Title", "New", False)
    assert original != compute_content_hash("uid", start, end, "Title", "Old", True)
    assert original != compute_content_hash("uid", start + timedelta(minutes=1), end, "Title", "Old", False)
