# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Registration and membership payloads can never carry a superadmin grant."""

from __future__ import annotations

import uuid

import pytest
from pydantic import BaseModel

from app.adapters.api.schemas.registration import RegistrationApprove, RegistrationCreate
from app.adapters.api.schemas.user_admin import MembershipAssign

_PAYLOADS: list[tuple[type[BaseModel], dict]] = [
    (RegistrationCreate, {"name": "Anna", "email": "anna@example.org"}),
    (
        RegistrationApprove,
        {"role": "VIEWER", "scope_type": "DISTRICT", "scope_id": str(uuid.uuid4())},
    ),
    (
        MembershipAssign,
        {"role": "VIEWER", "scope_type": "CONGREGATION", "scope_id": str(uuid.uuid4())},
    ),
]


@pytest.mark.parametrize(("schema", "payload"), _PAYLOADS)
def test_superadmin_fields_are_dropped(schema: type[BaseModel], payload: dict) -> None:
    parsed = schema.model_validate({**payload, "is_superadmin": True, "superadmin": True})
    assert "is_superadmin" not in schema.model_fields
    assert not {"is_superadmin", "superadmin"} & parsed.model_dump().keys()
