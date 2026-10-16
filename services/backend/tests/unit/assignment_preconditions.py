# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Conditional-write kwargs for tests that call the assignment writers directly."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from app.adapters.api.revisions import slot_revision


def precondition(slot: Any, instance: Any = None) -> dict[str, Any]:
    """``If-Match`` and instance repository matching the slot's current revision."""
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance
    return {"if_match": slot_revision(slot, instance), "instance_repo": instance_repo}
