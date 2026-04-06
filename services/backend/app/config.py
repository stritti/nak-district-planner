from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://nak:changeme@db:5432/nak_planner"
    secret_key: str = "replace-with-a-long-random-secret-key"
    app_env: str = "development"
    use_planning_slot_model: bool = False
    enable_dual_write_events: bool = True

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


settings = Settings()
