# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression contracts for issue #472's deployment hardening."""

from pathlib import Path

import pytest
import yaml

from app.config import Settings, production_guard

ROOT = Path(__file__).resolve().parents[4]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _services(path: str) -> dict:
    return yaml.safe_load(_read(path))["services"]


@pytest.mark.parametrize("service", ["frontend", "backend"])
def test_build_context_excludes_secrets_and_artifacts(service: str) -> None:
    patterns = _read(f"services/{service}/.dockerignore").splitlines()
    for excluded in (".env", ".env.*", "**/.env", "**/.env.*", ".git", "**/.git", "coverage", "**/coverage"):
        assert excluded in patterns, (service, excluded)
    assert "node_modules" in patterns or ".venv" in patterns


def test_frontend_is_unprivileged_and_serves_fresh_app_shell() -> None:
    dockerfile = _read("services/frontend/Dockerfile")
    nginx = _read("services/frontend/nginx.conf")
    real_ip = _read("services/frontend/15-real-ip-from.sh")
    assert "nginxinc/nginx-unprivileged:1." in dockerfile
    assert "FROM nginx:alpine" not in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "listen 8080;" in nginx
    assert "server_tokens off;" in nginx
    assert "include /tmp/real-ip-from.conf;" in nginx
    assert "out=/tmp/real-ip-from.conf" in real_ip
    assert "Cache-Control" in nginx and "no-cache" in nginx
    assert "/sw.js" in nginx
    assert "127.0.0.1:80:8080" in _read("docker-compose.yml")
    assert "loadbalancer.server.port=8080" in _read("deploy/compose/existing-traefik.yml")


def test_pwa_does_not_intercept_api_or_health_navigation() -> None:
    config = _read("services/frontend/vite.config.ts")
    assert "navigateFallbackDenylist" in config
    assert "api(?:\\/|$)" in config
    assert "health(?:\\?|$)" in config


def test_production_compose_restricts_app_processes() -> None:
    services = _services("docker-compose.prod.yml")
    for name in ("frontend", "backend", "worker", "beat"):
        service = services[name]
        assert service["read_only"] is True, name
        assert service["cap_drop"] == ["ALL"], name
        assert "no-new-privileges:true" in service["security_opt"], name
        assert service["deploy"]["resources"]["limits"]["memory"], name
        assert service["pids_limit"] > 0, name
        assert service.get("tmpfs"), name
    assert services["frontend"]["healthcheck"]["test"][-1].endswith(":8080/")
    assert services["worker"]["healthcheck"]["test"][0] == "CMD-SHELL"
    assert services["backend"]["depends_on"]["valkey"]["condition"] == "service_healthy"


def test_production_valkey_requires_password() -> None:
    valkey = _services("docker-compose.prod.yml")["valkey"]
    assert "VALKEY_PASSWORD" in valkey["environment"]
    assert "$"+"{VALKEY_PASSWORD:?" in valkey["environment"]["VALKEY_PASSWORD"]
    assert "requirepass" in str(valkey["command"])
    assert "VALKEY_PASSWORD" in str(valkey["healthcheck"]["test"])
    assert "$"+"{VALKEY_PASSWORD:?" in _read(".env.docker")


@pytest.mark.parametrize("path", [
    "idp-deploy/keycloak/docker-compose.yml",
    "idp-deploy/authentik/docker-compose.yml",
])
def test_standalone_idp_compose_requires_secrets(path: str) -> None:
    raw = _read(path)
    assert "version" not in yaml.safe_load(raw)
    assert "changeme" not in raw
    assert "InsecureSecretKeyChangeInProduction" not in raw
    assert ":?" in raw
    assert "auth.5tritti.de" not in raw


def test_idp_origin_is_https() -> None:
    keycloak = _services("idp-deploy/keycloak/docker-compose.yml")["keycloak"]
    assert keycloak["environment"]["KC_HOSTNAME"].startswith("https://")
    assert keycloak["environment"].get("KC_SPI_COOKIES_SECURE") != "false"
    authentik = _services("idp-deploy/authentik/docker-compose.yml")
    assert authentik["authentik"]["environment"]["AUTHENTIK_URL_SCHEME"] == "https"
    assert authentik["authentik-worker"]["environment"]["AUTHENTIK_URL_SCHEME"] == "https"


@pytest.mark.parametrize("value", ["changeme", "  changeme  ", "CHANGEME", ""])
def test_app_db_placeholder_rejected_in_production(monkeypatch, value: str) -> None:
    monkeypatch.setenv("VALKEY_PASSWORD", "secure-valkey-password")
    monkeypatch.setenv("APP_DB_PASSWORD", value)
    settings = Settings(
        _env_file=None,
        app_env="production",
        secret_key="a-secure-value-longer-than-32-characters",
        oidc_discovery_url="https://auth.example.org/.well-known/openid-configuration",
        oidc_client_secret="actual-oidc-secret",
        oidc_client_id="backend",
        backup_encrypt_key="backup@example.org",
        smtp_host="smtp.example.org",
        email_from_address="sender@example.org",
    )
    with pytest.raises(RuntimeError, match="APP_DB_PASSWORD"):
        production_guard(settings)


def test_restore_drill_checks_migrated_security_contract() -> None:
    drill = _read("scripts/restore-drill.sh")
    for item in (
        "alembic upgrade head", "pg_roles", "rolbypassrls",
        "pg_policies", "prosecdef", "has_table_privilege", "app_superadmin_config",
    ):
        assert item in drill
    assert "roles" in _read("scripts/backup.sh").lower()
