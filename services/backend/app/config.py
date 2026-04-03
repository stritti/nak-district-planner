from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://nak:changeme@db:5432/nak_planner"
    redis_url: str = "redis://redis:6379/0"
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
    oidc_scopes: str = "openid profile email"

    @field_validator("oidc_discovery_url", mode="after")
    @classmethod
    def validate_oidc_discovery_url(cls, v: str) -> str:
        """Validate OIDC discovery URL is not a placeholder."""
        if v == "https://oidc.example.com/.well-known/openid-configuration":
            raise ValueError("OIDC_DISCOVERY_URL must be configured (not example.com)")
        if not v.startswith("http"):
            raise ValueError("OIDC_DISCOVERY_URL must be a valid HTTP(S) URL")
        return v

    @field_validator("oidc_client_id", mode="after")
    @classmethod
    def validate_oidc_client_id(cls, v: str) -> str:
        """Validate OIDC client ID is configured."""
        if v == "replace-with-oidc-client-id":
            raise ValueError("OIDC_CLIENT_ID must be configured (not a placeholder)")
        return v

    @field_validator("oidc_client_secret", mode="after")
    @classmethod
    def validate_oidc_client_secret(cls, v: str) -> str:
        """Validate OIDC client secret is configured."""
        if v == "replace-with-oidc-client-secret":
            raise ValueError("OIDC_CLIENT_SECRET must be configured (not a placeholder)")
        return v

    def get_oidc_scopes_list(self) -> list[str]:
        """Parse OIDC_SCOPES string into list"""
        return [scope.strip() for scope in self.oidc_scopes.split() if scope.strip()]


settings = Settings()
