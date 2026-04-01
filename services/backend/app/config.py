from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://nak:changeme@db:5432/nak_planner"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "replace-with-a-long-random-secret-key"
    api_key: str = "replace-with-a-random-api-key"
    app_env: str = "development"

    # OpenTelemetry
    otel_enabled: bool = False
    otel_service_name: str = "nak-district-planner-backend"
    otel_endpoint: str = "http://localhost:4318"


settings = Settings()
