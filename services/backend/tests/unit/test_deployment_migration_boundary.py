# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Deployment boundary tests for database migrations."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_application_does_not_execute_alembic_upgrade() -> None:
    source = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "command.upgrade" not in source
    assert "from alembic import command" not in source
    assert "alembic.config" not in source


def test_runtime_application_fails_fast_on_schema_mismatch_without_migrating() -> None:
    source = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "await assert_database_schema_current(engine)" in source
    assert "except SchemaVersionError" in source


# Services that are not application runtimes: the database containers, the
# migration step itself and the cache. Every other service is a runtime and
# must pass the migration gate without owner credentials.
NON_RUNTIME_SERVICES = {"db", "db-test", "migrate", "valkey"}
OWNER_ONLY_ENV_FILES = {".env.db", ".env.docker.migrate"}


def _compose_services() -> dict:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    return compose["services"]


def _env_files(service: dict) -> list[str]:
    env_file = service.get("env_file", [])
    return [env_file] if isinstance(env_file, str) else list(env_file)


def _env_keys_and_values(filename: str) -> tuple[set[str], str]:
    keys: set[str] = set()
    values: list[str] = []
    for line in (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            keys.add(key.strip())
            values.append(value)
    return keys, "\n".join(values)


def _runtime_services() -> dict:
    return {
        name: service
        for name, service in _compose_services().items()
        if name not in NON_RUNTIME_SERVICES
    }


def test_runtime_services_wait_for_one_shot_migration() -> None:
    services = _compose_services()

    migrate = services["migrate"]
    assert migrate["command"] == "uv run alembic upgrade head"
    assert migrate["restart"] == "no"
    assert ".env.docker.migrate" in migrate["env_file"]

    runtime = _runtime_services()
    assert {"backend", "worker", "frontend"} <= set(runtime)
    for service_name, service in runtime.items():
        dependency = service.get("depends_on", {})
        assert isinstance(dependency, dict), f"{service_name}: depends_on must use conditions"
        assert dependency.get("migrate") == {"condition": "service_completed_successfully"}, (
            f"{service_name} must wait for the one-shot migration"
        )


def test_owner_password_cannot_reach_runtime_services() -> None:
    services = _compose_services()
    for owner_service in ("db", "db-test", "migrate"):
        assert ".env.db" in _env_files(services[owner_service])

    example_keys, _ = _env_keys_and_values(".env.example")
    assert "POSTGRES_PASSWORD" not in example_keys
    owner_keys, _ = _env_keys_and_values(".env.db.example")
    assert owner_keys == {"POSTGRES_PASSWORD"}

    for service_name, service in _runtime_services().items():
        assert "environment" not in service, f"{service_name}: use env files"
        for env_file in _env_files(service):
            assert env_file not in OWNER_ONLY_ENV_FILES, f"{service_name} loads {env_file}"
            keys, values = _env_keys_and_values(".env.example" if env_file == ".env" else env_file)
            assert "POSTGRES_PASSWORD" not in keys, f"{service_name}: {env_file}"
            assert "POSTGRES_PASSWORD" not in values, f"{service_name}: {env_file}"
            assert "MIGRATION_DATABASE_URL" not in keys, f"{service_name}: {env_file}"


def test_deployment_migration_runbook_documents_explicit_commands() -> None:
    runbook = (REPO_ROOT / "docs" / "deployment-migrations.md").read_text(encoding="utf-8")

    assert "docker compose run --no-deps --rm migrate" in runbook
    assert "docker compose run --no-deps --rm --build migrate" in runbook
    assert "uv run alembic upgrade head" in runbook
