"""Tests for the production_guard startup validator.

NOTE: the ``validate_oidc_settings`` model-validator inside ``Settings`` catches
placeholder OIDC values (OIDC_CLIENT_SECRET, OIDC_DISCOVERY_URL, OIDC_CLIENT_ID)
*before* ``production_guard`` runs.  The tests below therefore focus on the
unique value-add of ``production_guard``:
- ``SECRET_KEY`` length / default checks
- IDP provisioning checks
- non-HTTPS OIDC discovery warning
- Comprehensive multi-issue error grouping
"""

import pytest

from app.config import Settings, production_guard


def _valid_prod_settings(**overrides: object) -> Settings:
    """Helper: return a Settings object with all OIDC fields set to valid
    production values.  Individual fields can be overridden for testing."""
    kwargs: dict = {
        "app_env": "production",
        "secret_key": "a-32-char-string-abcdef1234567890",
        "oidc_client_secret": "a-very-secret-client-secret-12345",
        "oidc_discovery_url": ("https://auth.example.com/realms/nak-planner/"
                               ".well-known/openid-configuration"),
        "oidc_client_id": "nak-planner-backend",
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


# ── SECRET_KEY ──────────────────────────────────────────────────────────────

def test_production_guard_skipped_in_dev() -> None:
    """production_guard does nothing when APP_ENV is not 'production'."""
    settings = _valid_prod_settings(app_env="development",
                                    secret_key="replace-with-a-long-random-secret-key")
    production_guard(settings)  # should not raise


def test_production_guard_default_secret_key() -> None:
    settings = _valid_prod_settings(
        secret_key="replace-with-a-long-random-secret-key",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        production_guard(settings)


def test_production_guard_empty_secret_key() -> None:
    settings = _valid_prod_settings(secret_key="")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        production_guard(settings)


def test_production_guard_short_secret_key() -> None:
    settings = _valid_prod_settings(secret_key="too-short")
    with pytest.raises(RuntimeError, match="too short"):
        production_guard(settings)


# ── OIDC discovery HTTPS (model-validator checks URL, guard checks scheme) ──

def test_production_guard_non_https_oidc_discovery() -> None:
    settings = _valid_prod_settings(
        oidc_discovery_url="http://auth.example.com/.well-known/openid-configuration",
    )
    with pytest.raises(RuntimeError, match="HTTPS"):
        production_guard(settings)


# ── Comprehensive multi-issue error ─────────────────────────────────────────

def test_production_guard_all_defaults_at_once() -> None:
    """SECRET_KEY default + IDP misconfig produce a multi-issue error."""
    settings = _valid_prod_settings(
        secret_key="replace-with-a-long-random-secret-key",
        idp_provisioning_enabled=True,
        idp_provisioning_api_key=None,
        idp_provisioning_endpoint=None,
    )
    with pytest.raises(RuntimeError) as exc_info:
        production_guard(settings)
    msg = str(exc_info.value)
    assert "SECRET_KEY" in msg
    assert "IDP_PROVISIONING_API_KEY" in msg
    assert "IDP_PROVISIONING_ENDPOINT" in msg


# ── Valid config ────────────────────────────────────────────────────────────

def test_production_guard_valid_config() -> None:
    """All valid production values pass without errors."""
    settings = _valid_prod_settings()
    production_guard(settings)  # should not raise


# ── IDP provisioning ────────────────────────────────────────────────────────

def test_production_guard_idp_provisioning_checks() -> None:
    settings = _valid_prod_settings(
        idp_provisioning_enabled=True,
        idp_provisioning_api_key=None,
        idp_provisioning_endpoint=None,
    )
    with pytest.raises(RuntimeError) as exc_info:
        production_guard(settings)
    msg = str(exc_info.value)
    assert "IDP_PROVISIONING_API_KEY" in msg
    assert "IDP_PROVISIONING_ENDPOINT" in msg


def test_production_guard_idp_provisioning_https() -> None:
    settings = _valid_prod_settings(
        idp_provisioning_enabled=True,
        idp_provisioning_api_key="some-api-key",
        idp_provisioning_endpoint="http://idp.example.com/provision",
    )
    with pytest.raises(RuntimeError, match="HTTPS"):
        production_guard(settings)


def test_production_guard_idp_provisioning_valid() -> None:
    settings = _valid_prod_settings(
        idp_provisioning_enabled=True,
        idp_provisioning_api_key="some-api-key",
        idp_provisioning_endpoint="https://idp.example.com/provision",
    )
    production_guard(settings)  # should not raise
