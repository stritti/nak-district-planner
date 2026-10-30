# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests for the production_guard startup validator.

NOTE: the ``validate_oidc_settings`` model-validator inside ``Settings`` catches
placeholder OIDC values (OIDC_CLIENT_SECRET, OIDC_DISCOVERY_URL, OIDC_CLIENT_ID)
*before* ``production_guard`` runs. These tests cover additional guard rules.
"""

import pytest

from app.config import Settings, production_guard


@pytest.fixture(autouse=True)
def _safe_production_runtime_passwords(monkeypatch) -> None:
    """Most guard tests isolate one failure from otherwise safe runtime secrets."""
    monkeypatch.setenv("APP_DB_PASSWORD", "valid-app-db-password")
    monkeypatch.setenv("VALKEY_PASSWORD", "valid-valkey-password")



def _valid_prod_settings(**overrides: object) -> Settings:
    """Create deterministic, fully configured production settings for tests."""
    kwargs: dict = {
        "app_env": "production",
        "secret_key": "a-32-char-string-abcdef1234567890",
        "oidc_client_secret": "a-very-secret-client-secret-12345",
        "oidc_discovery_url": (
            "https://auth.example.com/realms/nak-planner/.well-known/openid-configuration"
        ),
        "oidc_client_id": "nak-planner-backend",
        "backup_encrypt_key": "backup@nak-district-planner.example",
        "smtp_host": "smtp.example.org",
        "email_from_address": "sender@example.org",
    }
    kwargs.update(overrides)
    return Settings(_env_file=None, **kwargs)


def test_production_guard_skipped_in_dev() -> None:
    settings = _valid_prod_settings(
        app_env="development", secret_key="replace-with-a-long-random-secret-key"
    )
    production_guard(settings)


def test_production_guard_default_secret_key() -> None:
    settings = _valid_prod_settings(secret_key="replace-with-a-long-random-secret-key")
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


def test_production_guard_non_https_oidc_discovery() -> None:
    settings = _valid_prod_settings(
        oidc_discovery_url="http://auth.example.com/.well-known/openid-configuration"
    )
    with pytest.raises(RuntimeError, match="HTTPS"):
        production_guard(settings)


def test_production_guard_all_defaults_at_once() -> None:
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


def test_production_guard_missing_backup_encrypt_key() -> None:
    settings = _valid_prod_settings(backup_encrypt_key=None)
    with pytest.raises(RuntimeError, match="BACKUP_ENCRYPT_KEY"):
        production_guard(settings)


def test_production_guard_empty_backup_encrypt_key() -> None:
    settings = _valid_prod_settings(backup_encrypt_key="")
    with pytest.raises(RuntimeError, match="BACKUP_ENCRYPT_KEY"):
        production_guard(settings)


def test_production_guard_with_backup_encrypt_key() -> None:
    settings = _valid_prod_settings(backup_encrypt_key="backup@nak-district-planner.example")
    production_guard(settings)


def test_production_guard_valid_config() -> None:
    production_guard(_valid_prod_settings())


def test_production_guard_missing_smtp_host() -> None:
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        production_guard(_valid_prod_settings(smtp_host=""))


def test_production_guard_missing_mail_sender() -> None:
    with pytest.raises(RuntimeError, match="EMAIL_FROM_ADDRESS"):
        production_guard(_valid_prod_settings(email_from_address=""))


def test_production_guard_incomplete_smtp_credentials() -> None:
    with pytest.raises(RuntimeError, match="SMTP_USER and SMTP_PASSWORD"):
        production_guard(_valid_prod_settings(smtp_user="someone", smtp_password=None))


def test_production_guard_rejects_smtp_credentials_without_starttls() -> None:
    with pytest.raises(RuntimeError, match="SMTP_STARTTLS"):
        production_guard(
            _valid_prod_settings(smtp_user="someone", smtp_password="password", smtp_starttls=False)
        )


def test_production_guard_allows_unauthenticated_relay_without_starttls() -> None:
    production_guard(_valid_prod_settings(smtp_starttls=False))


def test_production_guard_accepts_authenticated_smtp() -> None:
    production_guard(_valid_prod_settings(smtp_user="someone", smtp_password="password"))


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
    production_guard(settings)


@pytest.mark.parametrize("app_env", ["production", "development"])
def test_the_removed_keycloak_provisioner_refuses_startup_in_every_environment(app_env: str) -> None:
    with pytest.raises(ValueError, match="IDP_PROVISIONING_PROVIDER=keycloak") as exc_info:
        Settings(
            _env_file=None,
            app_env=app_env,
            idp_provisioning_enabled=True,
            idp_provisioning_provider="keycloak",
        )
    message = str(exc_info.value)
    assert "no Keycloak admin credential" in message
    assert "IDP_PROVISIONING_KEYCLOAK_*" in message
    assert "release-notes" in message


@pytest.mark.parametrize("provider", ["Keycloak", " KEYCLOAK ", "keycloak\n"])
def test_the_keycloak_guard_ignores_case_and_whitespace(provider: str) -> None:
    with pytest.raises(ValueError, match="IDP_PROVISIONING_PROVIDER=keycloak"):
        Settings(_env_file=None, idp_provisioning_enabled=True, idp_provisioning_provider=provider)


def test_the_webhook_provider_name_is_normalized() -> None:
    settings = Settings(_env_file=None, idp_provisioning_provider=" Webhook ")
    assert settings.idp_provisioning_provider == "webhook"


def test_keycloak_provider_is_harmless_while_provisioning_is_disabled() -> None:
    settings = Settings(
        _env_file=None, idp_provisioning_enabled=False, idp_provisioning_provider="keycloak"
    )
    assert settings.idp_provisioning_enabled is False


def test_the_webhook_provider_is_still_accepted() -> None:
    settings = Settings(
        _env_file=None,
        idp_provisioning_enabled=True,
        idp_provisioning_provider="webhook",
        idp_provisioning_endpoint="https://idp.example.com/provision",
        idp_provisioning_api_key="some-api-key",
    )
    assert settings.idp_provisioning_provider == "webhook"


def test_leftover_keycloak_variables_are_ignored_without_the_keycloak_provider(monkeypatch) -> None:
    monkeypatch.setenv("IDP_PROVISIONING_KEYCLOAK_CLIENT_SECRET", "left-over")
    monkeypatch.setenv("IDP_PROVISIONING_KEYCLOAK_BASE_URL", "https://kc.example.com")

    settings = Settings(_env_file=None)

    assert not hasattr(settings, "idp_provisioning_keycloak_client_secret")



def test_production_guard_oidc_client_secret_default() -> None:
    settings = Settings(
        _env_file=None,
        app_env="development",
        oidc_client_secret="replace-with-oidc-client-secret",
    )
    settings.app_env = "production"
    with pytest.raises(RuntimeError, match="OIDC_CLIENT_SECRET"):
        production_guard(settings)


def test_production_guard_oidc_discovery_url_default() -> None:
    settings = Settings(
        _env_file=None,
        app_env="development",
        oidc_discovery_url="https://oidc.example.com/.well-known/openid-configuration",
    )
    settings.app_env = "production"
    with pytest.raises(RuntimeError, match="OIDC_DISCOVERY_URL"):
        production_guard(settings)


def test_production_guard_oidc_client_id_default() -> None:
    settings = Settings(
        _env_file=None,
        app_env="development",
        oidc_client_id="replace-with-oidc-client-id",
    )
    settings.app_env = "production"
    with pytest.raises(RuntimeError, match="OIDC_CLIENT_ID"):
        production_guard(settings)


def test_insecure_calendar_urls_rejected_when_settings_are_built_in_production() -> None:
    # Enforced at Settings construction so every process (API, Celery worker,
    # beat) refuses it — not only the FastAPI lifespan's production_guard.
    with pytest.raises(ValueError, match="CALENDAR_ALLOW_INSECURE_URLS"):
        _valid_prod_settings(calendar_allow_insecure_urls=True)


def test_insecure_calendar_urls_allowed_outside_production() -> None:
    settings = _valid_prod_settings(app_env="development", calendar_allow_insecure_urls=True)
    assert settings.calendar_allow_insecure_urls is True


def test_calendar_insecure_urls_default_off() -> None:
    assert _valid_prod_settings().calendar_allow_insecure_urls is False


@pytest.mark.parametrize(
    "value",
    [
        "2001:db8::/33",  # not an RFC 6052 prefix length
        "2001:db8::/128",
        "10.0.0.0/8",  # IPv4
        "not-a-prefix",
        "2001:db8::1/64",  # host bits set
    ],
)
def test_invalid_calendar_nat64_prefixes_fail_settings_construction(value) -> None:
    with pytest.raises(ValueError, match="CALENDAR_NAT64_PREFIXES"):
        _valid_prod_settings(app_env="development", calendar_nat64_prefixes=value)


def test_valid_calendar_nat64_prefixes_are_parsed() -> None:
    settings = _valid_prod_settings(
        calendar_nat64_prefixes=" 2001:db8::/32 , 2001:db8:122:344::/96 "
    )
    assert [str(n) for n in settings.calendar_nat64_networks] == [
        "2001:db8::/32",
        "2001:db8:122:344::/96",
    ]
    assert _valid_prod_settings().calendar_nat64_networks == ()


@pytest.mark.parametrize("name", ["POSTGRES_PASSWORD", "MIGRATION_DATABASE_URL"])
def test_owner_credentials_in_runtime_environment_block_startup(monkeypatch, name) -> None:
    """A legacy ``.env`` may still carry the DB owner password into runtime services."""
    monkeypatch.setenv(name, "owner-secret")

    with pytest.raises(RuntimeError, match=name):
        production_guard(_valid_prod_settings())


def test_owner_credentials_check_ignores_development(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "changeme")

    production_guard(Settings(_env_file=None, app_env="development"))


def test_runtime_without_owner_credentials_passes(monkeypatch) -> None:
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)

    production_guard(_valid_prod_settings())


@pytest.mark.parametrize("name", ["APP_DB_PASSWORD", "VALKEY_PASSWORD"])
@pytest.mark.parametrize("placeholder", ["changeme", "CHANGEME", " password ", ""])
def test_production_guard_blocks_runtime_placeholder_passwords(monkeypatch, name, placeholder) -> None:
    monkeypatch.setenv(name, placeholder)
    with pytest.raises(RuntimeError, match=name):
        production_guard(_valid_prod_settings())


@pytest.mark.parametrize("name", ["APP_DB_PASSWORD", "VALKEY_PASSWORD"])
def test_production_guard_requires_runtime_passwords(monkeypatch, name) -> None:
    monkeypatch.delenv(name)
    with pytest.raises(RuntimeError, match=name):
        production_guard(_valid_prod_settings())

@pytest.mark.parametrize("name", ["APP_DB_PASSWORD", "VALKEY_PASSWORD"])
@pytest.mark.parametrize(
    "value", ["some@password", "with spaces", "a:b", "a/b", "a$bc", "äbc", "quoted'password"],
)
def test_production_guard_rejects_non_url_safe_runtime_passwords(
    monkeypatch, name: str, value: str,
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=rf"{name}.*URL-safe"):
        production_guard(_valid_prod_settings())


@pytest.mark.parametrize("name", ["APP_DB_PASSWORD", "VALKEY_PASSWORD"])
@pytest.mark.parametrize("value", ["A1bcdefghijk-_", "A1bcdefghijk.~"])
def test_production_guard_accepts_url_safe_runtime_passwords(
    monkeypatch, name: str, value: str,
) -> None:
    monkeypatch.setenv(name, value)
    production_guard(_valid_prod_settings())
