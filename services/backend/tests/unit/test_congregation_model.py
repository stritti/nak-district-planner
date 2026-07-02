"""Unit tests for Congregation domain model."""

from __future__ import annotations

import uuid

import pytest

from app.domain.models.congregation import Congregation
from app.domain.models.invitation import InvitationTargetType


class TestCongregation:
    """Tests for Congregation domain model."""

    def test_create_without_invitation_config(self):
        """Test creating a congregation without invitation config."""
        congregation = Congregation.create(
            name="Testgemeinde",
            district_id=uuid.uuid4(),
        )
        assert congregation.name == "Testgemeinde"
        assert congregation.invitation_target_type is None
        assert congregation.invitation_target_congregation_id is None
        assert congregation.invitation_external_note is None

    def test_create_with_district_congregation_target_missing_id(self):
        """Test that DISTRICT_CONGREGATION requires target congregation ID."""
        with pytest.raises(ValueError, match="invitation_target_congregation_id is required"):
            Congregation.create(
                name="Testgemeinde",
                district_id=uuid.uuid4(),
                invitation_target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                invitation_target_congregation_id=None,
            )

    def test_create_with_external_note_target_missing_note(self):
        """Test that EXTERNAL_NOTE requires external note."""
        with pytest.raises(ValueError, match="invitation_external_note is required"):
            Congregation.create(
                name="Testgemeinde",
                district_id=uuid.uuid4(),
                invitation_target_type=InvitationTargetType.EXTERNAL_NOTE,
                invitation_external_note="",
            )

    def test_create_with_district_congregation_target_success(self):
        """Test creating congregation with DISTRICT_CONGREGATION target."""
        target_id = uuid.uuid4()
        congregation = Congregation.create(
            name="Testgemeinde",
            district_id=uuid.uuid4(),
            invitation_target_type=InvitationTargetType.DISTRICT_CONGREGATION,
            invitation_target_congregation_id=target_id,
        )
        assert congregation.invitation_target_type == InvitationTargetType.DISTRICT_CONGREGATION
        assert congregation.invitation_target_congregation_id == target_id

    def test_create_with_external_note_target_success(self):
        """Test creating congregation with EXTERNAL_NOTE target."""
        congregation = Congregation.create(
            name="Testgemeinde",
            district_id=uuid.uuid4(),
            invitation_target_type=InvitationTargetType.EXTERNAL_NOTE,
            invitation_external_note="Bitte per Telefon kontaktieren",
        )
        assert congregation.invitation_target_type == InvitationTargetType.EXTERNAL_NOTE
        assert congregation.invitation_external_note == "Bitte per Telefon kontaktieren"
