# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Shared validation for recurrence patterns entering planning generation."""

from typing import Any


def recurrence_interval(pattern: dict[str, Any]) -> int:
    """Return the valid repeat interval; reject booleans and coercible strings."""
    interval = pattern.get("interval", 1)
    if type(interval) is not int or interval < 1:
        raise ValueError("Recurrence interval must be a positive integer")
    return interval
