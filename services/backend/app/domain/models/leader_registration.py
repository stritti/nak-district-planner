"""LeaderRegistration domain model — represents a self-registration request from a
new Amtstragender (service person) awaiting district-admin review.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from app.domain.models.leader import LeaderRank, SpecialRole
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role


class RegistrationStatus(str, Enum):
    """Workflow status for a leader registration request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class LeaderRegistration:
    """A registration request submitted by a prospective Amtstragender.

    The registrant fills in their details and optionally indicates which
    congregation they belong to.  A district administrator then approves
    (which creates an active Leader record) or rejects the request.
    """

    id: uuid.UUID
    district_id: uuid.UUID
    name: str
    email: str
    rank: LeaderRank | None
    congregation_id: uuid.UUID | None
    special_role: SpecialRole | None
    phone: str | None
    notes: str | None
    status: RegistrationStatus
    rejection_reason: str | None
    # OIDC subject of the registrant, if they were logged in when submitting
    user_sub: str | None
    assigned_role: Role | None
    assigned_scope_type: ScopeType | None
    assigned_scope_id: uuid.UUID | None
    approved_by_sub: str | None
    approved_at: datetime | None
    idp_provision_status: str | None
    idp_provision_error: str | None
    idp_provisioned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        *,
        district_id: uuid.UUID,
        name: str,
        email: str,
        rank: LeaderRank | None = None,
        congregation_id: uuid.UUID | None = None,
        special_role: SpecialRole | None = None,
        phone: str | None = None,
        notes: str | None = None,
        user_sub: str | None = None,
    ) -> "LeaderRegistration":
        now = datetime.now(UTC)
        return LeaderRegistration(
            id=uuid.uuid4(),
            district_id=district_id,
            name=name,
            email=email,
            rank=rank,
            congregation_id=congregation_id,
            special_role=special_role,
            phone=phone,
            notes=notes,
            status=RegistrationStatus.PENDING,
            rejection_reason=None,
            user_sub=user_sub,
            assigned_role=None,
            assigned_scope_type=None,
            assigned_scope_id=None,
            approved_by_sub=None,
            approved_at=None,
            idp_provision_status=None,
            idp_provision_error=None,
            idp_provisioned_at=None,
            created_at=now,
            updated_at=now,
        )
