"""Unit tests for app/adapters/idp/provisioning.py — get_idp_provisioner factory."""

from __future__ import annotations

from unittest.mock import patch

from app.adapters.idp.provisioning import get_idp_provisioner


def test_disabled_returns_none():
    with patch("app.adapters.idp.provisioning.settings") as mock_settings:
        mock_settings.idp_provisioning_enabled = False
        assert get_idp_provisioner() is None


def test_keycloak_provisioner_returned():
    with patch("app.adapters.idp.provisioning.settings") as mock_settings:
        mock_settings.idp_provisioning_enabled = True
        mock_settings.idp_provisioning_provider = "keycloak"
        mock_settings.idp_provisioning_keycloak_base_url = "https://kc.example.com"
        mock_settings.idp_provisioning_keycloak_realm = "nak"
        mock_settings.idp_provisioning_keycloak_admin_username = "admin"
        mock_settings.idp_provisioning_keycloak_admin_password = "secret"
        mock_settings.idp_provisioning_timeout_seconds = 10.0
        mock_settings.idp_provisioning_keycloak_invite_on_approval = True

        provisioner = get_idp_provisioner()
        assert provisioner is not None
        # Should be a KeycloakProvisioningAdapter
        assert "Keycloak" in type(provisioner).__name__


def test_keycloak_missing_config_returns_none():
    with patch("app.adapters.idp.provisioning.settings") as mock_settings:
        mock_settings.idp_provisioning_enabled = True
        mock_settings.idp_provisioning_provider = "keycloak"
        mock_settings.idp_provisioning_keycloak_base_url = None  # Missing
        mock_settings.idp_provisioning_keycloak_realm = "nak"
        mock_settings.idp_provisioning_keycloak_admin_username = "admin"
        mock_settings.idp_provisioning_keycloak_admin_password = "secret"

        assert get_idp_provisioner() is None


def test_webhook_provisioner_returned():
    with patch("app.adapters.idp.provisioning.settings") as mock_settings:
        mock_settings.idp_provisioning_enabled = True
        mock_settings.idp_provisioning_provider = "webhook"
        mock_settings.idp_provisioning_endpoint = "https://idp.example.com/provision"
        mock_settings.idp_provisioning_api_key = "key-123"
        mock_settings.idp_provisioning_timeout_seconds = 10.0

        provisioner = get_idp_provisioner()
        assert provisioner is not None
        assert "HttpIdp" in type(provisioner).__name__


def test_webhook_missing_endpoint_returns_none():
    with patch("app.adapters.idp.provisioning.settings") as mock_settings:
        mock_settings.idp_provisioning_enabled = True
        mock_settings.idp_provisioning_provider = "webhook"
        mock_settings.idp_provisioning_endpoint = None

        assert get_idp_provisioner() is None


def test_unknown_provider_returns_none():
    with patch("app.adapters.idp.provisioning.settings") as mock_settings:
        mock_settings.idp_provisioning_enabled = True
        mock_settings.idp_provisioning_provider = "ldap"

        assert get_idp_provisioner() is None
