"""app/config.py: Module."""

import importlib.metadata
import ipaddress
import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.models.calendar_integration import SyncDeleteMode

_NAT64_PREFIX_LENGTHS = {32, 40, 48, 56, 64, 96}


def _parse_nat64_prefixes(value: str) -> tuple[ipaddress.IPv6Network, ...]:
    networks = []
    for item in filter(None, (part.strip() for part in value.split(","))):
        try:
            network = ipaddress.ip_network(item)
        except ValueError as exc:
            raise ValueError(f"CALENDAR_NAT64_PREFIXES: invalid prefix {item!r}") from exc
        if not isinstance(network, ipaddress.IPv6Network):
            raise ValueError(f"CALENDAR_NAT64_PREFIXES: {item!r} is not IPv6")
        if network.prefixlen not in _NAT64_PREFIX_LENGTHS:
            raise ValueError(
                f"CALENDAR_NAT64_PREFIXES: {item!r} must have length 32, 40, 48, 56, 64 or 96"
            )
        networks.append(network)
    return tuple(networks)


class Settings(BaseSettings):
    """Settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://nak:changeme@db:5432/nak_planner"
    migration_database_url: str | None = None
    valkey_url: str = "valkey://valkey:6379/0"
    secret_key: str = "replace-with-a-long-random-secret-key"
    app_env: str = "development"

    # SMTP outbound delivery (SMTP is selected only in production)
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    smtp_timeout_seconds: float = Field(default=10.0, gt=0)
    email_from_address: str = ""
    email_footer: str = ""

    # Daily SLOT_UNASSIGNED scan: how many days ahead open gaps are reported
    slot_gap_scan_days: int = Field(default=28, ge=0, le=366)

    # Backup/Restore (scripts/backup.sh, scripts/restore.sh)
    backup_encrypt_key: str | None = None

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
    use_series_generation: bool = True
    conflict_check_enabled: bool = True
    sync_delete_mode: SyncDeleteMode = SyncDeleteMode.MARK_CANCELLED
    sync_expected_duration_minutes: int = Field(default=90, ge=1)
    min_travel_minutes: int = Field(default=30, ge=0)
    # Dev only: allow http:// and private/loopback calendar URLs (local test
    # servers). Rejected by production_guard — SSRF protection, see #463.
    calendar_allow_insecure_urls: bool = False
    # Network-specific NAT64 prefixes (RFC 6052) of the host's DNS64/NAT64
    # setup, comma-separated IPv6 CIDRs of length 32/40/48/56/64/96. Addresses
    # inside them are unwrapped and the embedded IPv4 is checked (SSRF, #463).
    calendar_nat64_prefixes: str = ""

    # Version check (display only — the app never executes updates, see #469)
    ghcr_owner: str = "stritti"
    ghcr_repo: str = "nak-district-planner"

    @field_validator("calendar_nat64_prefixes")
    @classmethod
    def validate_calendar_nat64_prefixes(cls, value: str) -> str:
        _parse_nat64_prefixes(value)
        return value

    @property
    def calendar_nat64_networks(self) -> tuple[ipaddress.IPv6Network, ...]:
        return _parse_nat64_prefixes(self.calendar_nat64_prefixes)

    @model_validator(mode="after")
    def reject_insecure_calendar_urls_in_production(self) -> Settings:
        """Fail every process (API, worker, beat) at settings load, not only the API lifespan."""
        if self.app_env == "production" and self.calendar_allow_insecure_urls:
            raise ValueError(
                "CALENDAR_ALLOW_INSECURE_URLS must be false in production (SSRF protection)"
            )
        return self

    @model_validator(mode="after")
    def validate_oidc_settings(self) -> Settings:
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


OWNER_CREDENTIAL_VARIABLES = ("POSTGRES_PASSWORD", "MIGRATION_DATABASE_URL")


def production_guard(settings: Settings) -> None:
    """Validate production configuration and block startup on critical issues.

    Called during app startup when ``APP_ENV=production``.  Raises
    ``RuntimeError`` for each unsafe setting so that the process fails
    early with an informative message.
    """
    if settings.app_env != "production":
        return

    errors: list[str] = []

    # Owner credentials belong to the db/migrate services only (.env.db). A
    # legacy .env may still carry them into runtime containers on upgrade.
    errors.extend(
        f"{name} must not be set for runtime services (move it to .env.db)"
        for name in OWNER_CREDENTIAL_VARIABLES
        if os.environ.get(name)
    )

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

    # Backups must be encrypted in production (scripts/backup.sh refuses without this too)
    if not settings.backup_encrypt_key:
        errors.append(
            "BACKUP_ENCRYPT_KEY must be configured in production "
            "(GPG recipient/key ID used by scripts/backup.sh to encrypt dumps)"
        )

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

    # Outbound mail must never silently fall back to logging in production.
    if not settings.smtp_host:
        errors.append("SMTP_HOST must be configured in production")
    if not settings.email_from_address:
        errors.append("EMAIL_FROM_ADDRESS must be configured in production")
    if bool(settings.smtp_user) != bool(settings.smtp_password):
        errors.append("SMTP_USER and SMTP_PASSWORD must both be supplied or both absent")

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
