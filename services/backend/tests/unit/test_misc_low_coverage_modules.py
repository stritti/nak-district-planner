from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.auth.claims_validation import (
    InvalidMembershipClaimError,
    validate_membership_claims,
    validate_token_claim_consistency,
)
from app.adapters.auth.notifications import can_act_on_notification, can_view_notification
from app.adapters.idp.provisioning import HttpIdpProvisioningAdapter, IdpProvisioningError
from app.application.init import seed_canonical_roles
from app.config import Settings
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


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
    with patch("app.adapters.idp.provisioning.httpx.AsyncClient", return_value=client_ctx):
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
    with patch("app.adapters.idp.provisioning.httpx.AsyncClient", return_value=client_ctx2):
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
