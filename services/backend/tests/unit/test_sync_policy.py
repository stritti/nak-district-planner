# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from dataclasses import fields

import pytest

from app.domain.models.event_instance import EventInstance, SyncState
from app.domain.models.planning_slot import PlanningSlot
from app.domain.services.sync_policy import (
    FIELD_AUTHORITY,
    SyncFieldAuthority,
    classify_field,
    inbound_state,
    internal_state,
)


def test_all_persisted_fields_have_explicit_authority():
    for model in (EventInstance, PlanningSlot):
        assert {field.name for field in fields(model)} <= FIELD_AUTHORITY.keys()
    assert classify_field("title") == SyncFieldAuthority.SOFT
    assert classify_field("planning_time") == SyncFieldAuthority.STRUCTURAL
    assert classify_field("actual_start_at") == SyncFieldAuthority.CONDITIONAL


def test_unknown_fields_fail_closed_and_log(caplog):
    assert classify_field("future_field") == SyncFieldAuthority.STRUCTURAL
    assert "future_field" in caplog.text


@pytest.mark.parametrize("state", list(SyncState))
def test_duplicate_payload_preserves_state(state):
    assert inbound_state(state, changed=False) == state


@pytest.mark.parametrize("state,expected", [
    (SyncState.CLEAN, SyncState.DIRTY_EXTERNAL),
    (SyncState.DIRTY_EXTERNAL, SyncState.DIRTY_EXTERNAL),
    (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT),
    (SyncState.CONFLICT, SyncState.CONFLICT),
])
def test_inbound_transition(state, expected):
    assert inbound_state(state, changed=True) == expected


@pytest.mark.parametrize("state,expected", [
    (SyncState.CLEAN, SyncState.DIRTY_INTERNAL),
    (SyncState.DIRTY_INTERNAL, SyncState.DIRTY_INTERNAL),
    (SyncState.DIRTY_EXTERNAL, SyncState.CONFLICT),
    (SyncState.CONFLICT, SyncState.CONFLICT),
])
def test_internal_transition(state, expected):
    assert internal_state(state) == expected
