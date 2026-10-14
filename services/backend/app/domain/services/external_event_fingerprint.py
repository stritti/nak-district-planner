# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Canonical fingerprint of provider event fields during synchronization."""

import hashlib
from datetime import datetime


def compute_content_hash(
    uid: str,
    start_at: datetime,
    end_at: datetime,
    title: str,
    description: str | None = None,
    is_cancelled: bool = False,
) -> str:
    """Hash sync-relevant fields without provider-specific revision metadata."""
    payload = f"{uid}|{start_at}|{end_at}|{title}|{description}|{is_cancelled}"
    return hashlib.sha256(payload.encode()).hexdigest()
