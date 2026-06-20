"""app/config.py: Module."""

import importlib.metadata

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://nak:changeme@db:5432/nak_planner"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "replace-with-a-long-random-secret-key"
    app_env: str = "development"

    # OpenTelemetry
    otel_enabled: bool = False
    otel_service_name: str = "nak-district-planner-backend"
    otel_endpoint: str = "http://localhost:4318"

    # OIDC Configuration (provider-agnostic)
    oidc_discovery_url: str = "https://oidc.example.com/.well-known/openid-configuration"
    oidc_client_id: str = "replace-with-oidc-client-id"
    oidc_client_secret: str = "replace-with-oidc-client-secret"
    oidc_issuer: str | None = (
        None  # Can be overridden; typically discovered from OIDC_DISCOVERY_URL
    )
    oidc_audience: str | None = None
    oidc_scopes: str = "openid profile email"
    superadmin_sub: str | None = None
    idp_provisioning_enabled: bool = False
    idp_provisioning_provider: str = "webhook"
    idp_provisioning_endpoint: str | None = None
    idp_provisioning_api_key: str | None = None
    idp_provisioning_timeout_seconds: float = 10.0
    idp_provisioning_keycloak_base_url: str | None = None
    idp_provisioning_keycloak_realm: str | None = None
    idp_provisioning_keycloak_admin_username: str | None = None
    idp_provisioning_keycloak_admin_password: str | None = None
    idp_provisioning_keycloak_invite_on_approval: bool = True
    startup_generate_draft_services: bool = False

    # Version check & self-update
    ghcr_owner: str = "stritti"
    ghcr_repo: str = "nak-district-planner"
    update_mode: str = "manual"
    docker_compose_dir: str = ""

    @model_validator(mode="after")
    def validate_oidc_settings(self) -> "Settings":
        """Validate OIDC settings are properly configured in production."""
        if self.app_env != "production":
            return self
        if self.oidc_discovery_url == "https://oidc.example.com/.well-known/openid-configuration":
            raise ValueError("OIDC_DISCOVERY_URL must be configured (not example.com)")
        if not self.oidc_discovery_url.startswith("http"):
            raise ValueError("OIDC_DISCOVERY_URL must be a valid HTTP(S) URL")
        if self.oidc_client_id == "replace-with-oidc-client-id":
            raise ValueError("OIDC_CLIENT_ID must be configured (not a placeholder)")
        if self.oidc_client_secret == "replace-with-oidc-client-secret":
            raise ValueError("OIDC_CLIENT_SECRET must be configured (not a placeholder)")
        return self

    def get_oidc_scopes_list(self) -> list[str]:
        """Parse OIDC_SCOPES string into list"""
        return [scope.strip() for scope in self.oidc_scopes.split() if scope.strip()]

    @property
    def app_version(self) -> str:
        """Return the running application version from package metadata."""
        try:
            return importlib.metadata.version("nak-district-planner-backend")
        except importlib.metadata.PackageNotFoundError:
            return "0.0.0"


def production_guard(settings: Settings) -> None:
    """Validate production configuration and block startup on critical issues.

    Called during app startup when ``APP_ENV=production``.  Raises
    ``RuntimeError`` for each unsafe setting so that the process fails
    early with an informative message.
    """
    if settings.app_env != "production":
        return

    errors: list[str] = []

    # SECRET_KEY must be non-default and have sufficient entropy
    if settings.secret_key in (
        "replace-with-a-long-random-secret-key",
        "",
    ):
        errors.append(
            "SECRET_KEY must be changed from the default value "
            '(generate one with: python -c "import secrets; print(secrets.token_hex(32))")'
        )
    if len(settings.secret_key) < 32:
        errors.append(f"SECRET_KEY is too short ({len(settings.secret_key)} chars, minimum 32)")

    # OIDC_CLIENT_SECRET must not be a placeholder
    if settings.oidc_client_secret in (
        "replace-with-oidc-client-secret",
        "",
    ):
        errors.append("OIDC_CLIENT_SECRET must be changed from the default value")

    # OIDC discovery URL
    if settings.oidc_discovery_url in (
        "https://oidc.example.com/.well-known/openid-configuration",
        "",
    ):
        errors.append("OIDC_DISCOVERY_URL must be changed from the default value")
    if not settings.oidc_discovery_url.startswith("https://"):
        errors.append("OIDC_DISCOVERY_URL should use HTTPS in production")

    # OIDC client ID
    if settings.oidc_client_id in (
        "replace-with-oidc-client-id",
        "",
    ):
        errors.append("OIDC_CLIENT_ID must be changed from the default value")

    # IDP provisioning secrets — validate only the fields relevant to the selected provider
    if settings.idp_provisioning_enabled:
        if settings.idp_provisioning_provider == "webhook":
            if settings.idp_provisioning_api_key in (None, ""):
                errors.append(
                    "IDP_PROVISIONING_API_KEY must be configured when provisioning is enabled"
                )
            if not settings.idp_provisioning_endpoint:
                errors.append(
                    "IDP_PROVISIONING_ENDPOINT must be configured when provisioning is enabled"
                )
            if (
                settings.idp_provisioning_endpoint
                and not settings.idp_provisioning_endpoint.startswith("https://")
            ):
                errors.append("IDP_PROVISIONING_ENDPOINT should use HTTPS in production")
        elif settings.idp_provisioning_provider == "keycloak":
            if not settings.idp_provisioning_keycloak_base_url:
                errors.append(
                    "IDP_PROVISIONING_KEYCLOAK_BASE_URL must be configured when using keycloak provider"
                )
            if not settings.idp_provisioning_keycloak_realm:
                errors.append(
                    "IDP_PROVISIONING_KEYCLOAK_REALM must be configured when using keycloak provider"
                )
            if not settings.idp_provisioning_keycloak_admin_username:
                errors.append(
                    "IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME must be configured when using keycloak provider"
                )
            if settings.idp_provisioning_keycloak_admin_password in (
                None,
                "",
                "replace-with-admin-password",
            ):
                errors.append(
                    "IDP_PROVISIONING_KEYCLOAK_ADMIN_PASSWORD must be changed from the default value"
                )

    if errors:
        raise RuntimeError(
            f"Production configuration check failed — {len(errors)} issue(s):\n"
            + "\n".join(f"  • {e}" for e in errors)
        )


settings = Settings()
