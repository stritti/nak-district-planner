from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.auth.claims_validation import (
    InvalidMembershipClaimError,
    validate_membership_claims,
    validate_token_claim_consistency,
)
from app.adapters.auth.notifications import can_act_on_notification, can_view_notification
from app.adapters.idp.base import IdpProvisioningError
from app.adapters.idp.keycloak_provisioner import KeycloakProvisioningAdapter
from app.adapters.idp.webhook_provisioner import HttpIdpProvisioningAdapter
from app.application.init import seed_canonical_roles
from app.config import Settings
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationTargetType,
)
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role
from app.domain.models.service_assignment import ServiceAssignment
from app.celery_app import _make_sync_db_url
from app.config import Settings


def test_validate_membership_claims_success_and_missing() -> None:
    claims = {
        "sub": "oidc|u1",
        "memberships": [
            {
                "role": "PLANNER",
                "scope_type": "DISTRICT",
                "scope_id": str(uuid.uuid4()),
            }
        ],
    }
    parsed = validate_membership_claims(claims)
    assert len(parsed) == 1

    assert validate_membership_claims({"sub": "u"}) == []


def test_validate_membership_claims_invalid_cases() -> None:
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": "not-list"})
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": [{}]})
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims(
            {
                "memberships": [
                    {"role": "NOPE", "scope_type": "DISTRICT", "scope_id": str(uuid.uuid4())}
                ]
            }
        )
    # claim is not a dict
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": [123]})
    # missing scope_type
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": [{"role": "VIEWER", "scope_id": str(uuid.uuid4())}]})
    # missing scope_id
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": [{"role": "VIEWER", "scope_type": "DISTRICT"}]})
    # invalid scope_type enum
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": [{"role": "VIEWER", "scope_type": "GARBAGE", "scope_id": str(uuid.uuid4())}]})
    # invalid scope_id UUID
    with pytest.raises(InvalidMembershipClaimError):
        validate_membership_claims({"memberships": [{"role": "VIEWER", "scope_type": "DISTRICT", "scope_id": "kein-uuid"}]})


def test_validate_token_claim_consistency() -> None:
    m = Membership.create(
        user_sub="u",
        role=Role.VIEWER,
        scope_type=ScopeType.DISTRICT,
        scope_id=uuid.uuid4(),
    )
    assert validate_token_claim_consistency({"memberships": [1]}, [m]) is True
    assert validate_token_claim_consistency({"memberships": [1]}, []) is False
    assert validate_token_claim_consistency({}, []) is True


def test_notification_helpers_delegate_to_permissions() -> None:
    auth = type("A", (), {"memberships": []})()
    did = uuid.uuid4()
    with patch("app.adapters.auth.permissions.has_role_in_district", return_value=True):
        assert can_view_notification(auth, did) is True
        assert can_act_on_notification(auth, did) is True


@pytest.mark.asyncio
async def test_seed_canonical_roles_noop() -> None:
    await seed_canonical_roles(AsyncMock())


@pytest.mark.asyncio
async def test_idp_provisioning_adapter_success_and_failures() -> None:
    adapter = HttpIdpProvisioningAdapter(
        endpoint="https://idp.example.com/provision",
        api_key="k",
        timeout_seconds=2,
    )

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"status": "INVITED", "user_sub": "oidc|u1"}

    client_ctx = AsyncMock()
    client_ctx.__aenter__.return_value.post = AsyncMock(return_value=response)
    with patch("app.adapters.idp.webhook_provisioner.httpx.AsyncClient", return_value=client_ctx):
        result = await adapter.provision_user(
            email="u@example.com",
            name="User",
            district_id=str(uuid.uuid4()),
            registration_id=str(uuid.uuid4()),
            role="PLANNER",
            scope_type="DISTRICT",
            scope_id=str(uuid.uuid4()),
        )
    assert result.status == "INVITED"

    bad = AsyncMock()
    bad.status_code = 500
    bad.text = "err"
    client_ctx2 = AsyncMock()
    client_ctx2.__aenter__.return_value.post = AsyncMock(return_value=bad)
    with patch("app.adapters.idp.webhook_provisioner.httpx.AsyncClient", return_value=client_ctx2):
        with pytest.raises(IdpProvisioningError):
            await adapter.provision_user(
                email="u@example.com",
                name="User",
                district_id=str(uuid.uuid4()),
                registration_id=str(uuid.uuid4()),
                role="PLANNER",
                scope_type="DISTRICT",
                scope_id=str(uuid.uuid4()),
            )


@pytest.mark.asyncio
async def test_keycloak_provisioning_adapter_create_and_invite() -> None:
    adapter = KeycloakProvisioningAdapter(
        base_url="https://kc.example.com",
        realm="nak-planner",
        admin_username="admin",
        admin_password="secret",
        timeout_seconds=2,
        invite_on_approval=True,
    )

    token_resp = MagicMock(status_code=200)
    token_resp.json.return_value = {"access_token": "t"}

    lookup_empty = MagicMock(status_code=200)
    lookup_empty.json.return_value = []

    create_resp = MagicMock(
        status_code=201, headers={"Location": "https://kc/admin/realms/nak/users/u123"}
    )

    invite_resp = MagicMock(status_code=204, text="")

    client_ctx = AsyncMock()
    c = client_ctx.__aenter__.return_value
    c.post = AsyncMock(side_effect=[token_resp, create_resp])
    c.get = AsyncMock(return_value=lookup_empty)
    c.put = AsyncMock(return_value=invite_resp)

    with patch("app.adapters.idp.keycloak_provisioner.httpx.AsyncClient", return_value=client_ctx):
        result = await adapter.provision_user(
            email="u@example.com",
            name="User Name",
            district_id=str(uuid.uuid4()),
            registration_id=str(uuid.uuid4()),
            role="PLANNER",
            scope_type="DISTRICT",
            scope_id=str(uuid.uuid4()),
        )
    assert result.status == "CREATED_INVITED"
    assert result.user_sub == "u123"


@pytest.mark.asyncio
async def test_keycloak_provisioning_adapter_existing_user() -> None:
    adapter = KeycloakProvisioningAdapter(
        base_url="https://kc.example.com",
        realm="nak-planner",
        admin_username="admin",
        admin_password="secret",
        timeout_seconds=2,
        invite_on_approval=False,
    )

    token_resp = MagicMock(status_code=200)
    token_resp.json.return_value = {"access_token": "t"}

    lookup_existing = MagicMock(status_code=200)
    lookup_existing.json.return_value = [{"id": "existing-1"}]

    client_ctx = AsyncMock()
    c = client_ctx.__aenter__.return_value
    c.post = AsyncMock(return_value=token_resp)
    c.get = AsyncMock(return_value=lookup_existing)

    with patch("app.adapters.idp.keycloak_provisioner.httpx.AsyncClient", return_value=client_ctx):
        result = await adapter.provision_user(
            email="u@example.com",
            name="User",
            district_id=str(uuid.uuid4()),
            registration_id=str(uuid.uuid4()),
            role="PLANNER",
            scope_type="DISTRICT",
            scope_id=str(uuid.uuid4()),
        )
    assert result.status == "EXISTING"
    assert result.user_sub == "existing-1"


def test_settings_parsing_and_validation() -> None:
    s = Settings(
        app_env="development",
        oidc_scopes="openid profile email",
    )
    assert s.get_oidc_scopes_list() == ["openid", "profile", "email"]

    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            oidc_discovery_url="https://oidc.example.com/.well-known/openid-configuration",
            oidc_client_id="replace-with-oidc-client-id",
            oidc_client_secret="replace-with-oidc-client-secret",
        )


def test_role_comparison_operators() -> None:
    """Test Role comparison operators (__gt__, __ge__)."""
    # __gt__
    assert Role.DISTRICT_ADMIN > Role.PLANNER
    assert Role.PLANNER > Role.VIEWER
    assert not Role.VIEWER > Role.VIEWER
    assert not Role.VIEWER > Role.DISTRICT_ADMIN
    # __ge__
    assert Role.DISTRICT_ADMIN >= Role.DISTRICT_ADMIN
    assert Role.DISTRICT_ADMIN >= Role.VIEWER
    assert not Role.VIEWER >= Role.DISTRICT_ADMIN


def test_service_assignment_create_validation() -> None:
    """ServiceAssignment.create raises ValueError when both leader_id and leader_name are unset."""
    with pytest.raises(ValueError, match="leader_id oder leader_name"):
        ServiceAssignment.create(event_id=uuid.uuid4(), leader_id=None, leader_name="")


def test_service_assignment_create_with_leader_id() -> None:
    """ServiceAssignment.create with leader_id succeeds."""
    assignment = ServiceAssignment.create(event_id=uuid.uuid4(), leader_id=uuid.uuid4())
    assert assignment.leader_id is not None
    assert assignment.status.value == "OPEN"


def test_congregation_invitation_create_validation() -> None:
    """CongregationInvitation.create validates target_congregation_id for DISTRICT_CONGREGATION."""
    with pytest.raises(ValueError, match="target_congregation_id"):
        CongregationInvitation.create(
            source_event_id=uuid.uuid4(),
            source_planning_slot_id=uuid.uuid4(),
            source_congregation_id=uuid.uuid4(),
            target_type=InvitationTargetType.DISTRICT_CONGREGATION,
            target_congregation_id=None,
        )


def test_make_sync_db_url_valid() -> None:
    """_make_sync_db_url converts async URL to sync URL."""
    result = _make_sync_db_url("postgresql+asyncpg://user:pass@localhost:5432/db")
    assert result == "postgresql+psycopg2://user:pass@localhost:5432/db"


def test_settings_production_oidc_discovery_url_must_be_http() -> None:
    """Settings validator rejects non-HTTP OIDC discovery URLs in production."""
    with pytest.raises(ValueError, match="HTTP"):
        Settings(
            app_env="production",
            oidc_discovery_url="ftp://oidc.example.com/.well-known/openid-configuration",
            oidc_client_id="real-client-id",
            oidc_client_secret="real-client-secret",
        )


def test_settings_production_oidc_client_id_must_not_be_placeholder() -> None:
    with pytest.raises(ValueError, match="OIDC_CLIENT_ID"):
        Settings(
            app_env="production",
            oidc_discovery_url="https://custom-auth.example.com/.well-known/openid-configuration",
            oidc_client_id="replace-with-oidc-client-id",
            oidc_client_secret="real-client-secret",
        )


def test_settings_production_oidc_client_secret_must_not_be_placeholder() -> None:
    with pytest.raises(ValueError, match="OIDC_CLIENT_SECRET"):
        Settings(
            app_env="production",
            oidc_discovery_url="https://custom-auth.example.com/.well-known/openid-configuration",
            oidc_client_id="real-client-id",
            oidc_client_secret="replace-with-oidc-client-secret",
        )


def test_settings_app_version_package_not_found() -> None:
    """app_version falls back to '0.0.0' when package is not installed."""
    from unittest.mock import patch
    import importlib.metadata

    with patch.object(importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError):
        s = Settings(app_env="development", oidc_scopes="openid profile")
        assert s.app_version == "0.0.0"


def test_make_sync_db_url_invalid() -> None:
    """_make_sync_db_url raises ValueError for non-asyncpg URLs."""
    with pytest.raises(ValueError, match="DATABASE_URL must start with"):
        _make_sync_db_url("sqlite:///db.sqlite3")


def test_congregation_invitation_external_note_validation() -> None:
    """CongregationInvitation.create validates external_target_note for EXTERNAL_NOTE."""
    with pytest.raises(ValueError, match="external_target_note"):
        CongregationInvitation.create(
            source_event_id=uuid.uuid4(),
            source_planning_slot_id=uuid.uuid4(),
            source_congregation_id=uuid.uuid4(),
            target_type=InvitationTargetType.EXTERNAL_NOTE,
            external_target_note=None,
        )


def test_invitation_target_create_requires_congregation_id_for_district() -> None:
    """InvitationTargetCreate validates congregation_id for DISTRICT_CONGREGATION."""
    from app.adapters.api.schemas.invitation import InvitationTargetCreate

    with pytest.raises(ValueError, match="target_congregation_id is required"):
        InvitationTargetCreate(
            target_type=InvitationTargetType.DISTRICT_CONGREGATION,
            target_congregation_id=None,
        )


def test_invitation_target_create_rejects_external_note_for_district() -> None:
    """InvitationTargetCreate rejects external_target_note for DISTRICT_CONGREGATION."""
    from app.adapters.api.schemas.invitation import InvitationTargetCreate

    with pytest.raises(ValueError, match="external_target_note must be empty"):
        InvitationTargetCreate(
            target_type=InvitationTargetType.DISTRICT_CONGREGATION,
            target_congregation_id=uuid.uuid4(),
            external_target_note="should not be set",
        )


def test_invitation_target_create_requires_note_for_external() -> None:
    """InvitationTargetCreate requires external_target_note for EXTERNAL_NOTE."""
    from app.adapters.api.schemas.invitation import InvitationTargetCreate

    with pytest.raises(ValueError, match="external_target_note is required"):
        InvitationTargetCreate(
            target_type=InvitationTargetType.EXTERNAL_NOTE,
            external_target_note=None,
        )


def test_invitation_target_create_rejects_congregation_id_for_external() -> None:
    """InvitationTargetCreate rejects target_congregation_id for EXTERNAL_NOTE."""
    from app.adapters.api.schemas.invitation import InvitationTargetCreate

    with pytest.raises(ValueError, match="target_congregation_id must be empty"):
        InvitationTargetCreate(
            target_type=InvitationTargetType.EXTERNAL_NOTE,
            external_target_note="A note",
            target_congregation_id=uuid.uuid4(),
        )


def test_overwrite_decision_request_rejects_pending() -> None:
    """OverwriteDecisionRequest rejects PENDING_OVERWRITE as a decision."""
    from app.adapters.api.schemas.invitation import OverwriteDecisionRequest, OverwriteDecisionStatus

    with pytest.raises(ValueError, match="ACCEPTED or REJECTED"):
        OverwriteDecisionRequest(
            decision=OverwriteDecisionStatus.PENDING_OVERWRITE,
        )


def test_overwrite_decision_request_accepted() -> None:
    """OverwriteDecisionRequest accepts ACCEPTED."""
    from app.adapters.api.schemas.invitation import OverwriteDecisionRequest, OverwriteDecisionStatus

    req = OverwriteDecisionRequest(decision=OverwriteDecisionStatus.ACCEPTED)
    assert req.decision == OverwriteDecisionStatus.ACCEPTED


def test_service_assignment_create_rejects_both_none() -> None:
    """ServiceAssignmentCreate rejects leader_id and leader_name both None."""
    from app.adapters.api.schemas.service_assignment import ServiceAssignmentCreate

    with pytest.raises(ValueError, match="leader_id oder leader_name"):
        ServiceAssignmentCreate(leader_id=None, leader_name=None)


def test_service_assignment_create_accepts_leader_name() -> None:
    """ServiceAssignmentCreate accepts leader_name alone."""
    from app.adapters.api.schemas.service_assignment import ServiceAssignmentCreate

    req = ServiceAssignmentCreate(leader_name="Pr. Müller")
    assert req.leader_name == "Pr. Müller"
    assert req.leader_id is None


def test_planning_series_response_from_orm() -> None:
    """PlanningSeriesResponse.from_orm converts domain model to response."""
    from app.domain.models.planning_series import PlanningSeries
    from app.adapters.api.schemas.planning_series import PlanningSeriesResponse

    district_id = uuid.uuid4()
    series = PlanningSeries.create(
        district_id=district_id,
        default_planning_time=time(9, 30),
        recurrence_pattern={"frequency": "weekly", "interval": 1},
        active_from=date(2026, 1, 1),
    )
    response = PlanningSeriesResponse.from_orm(series)
    assert response.id == series.id
    assert response.district_id == district_id
    assert response.default_planning_time == time(9, 30)
    assert response.recurrence_pattern == {"frequency": "weekly", "interval": 1}
    assert response.is_active is True
