# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _service_block(filename: str, service: str) -> str:
    lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()
    marker = f"  {service}:"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise AssertionError(f"Service {service!r} missing from {filename}") from exc

    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            break
        block.append(line)
    return "\n".join(block)


def _env_entries(filename: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        assert separator, f"Malformed env line in {filename}: {line!r}"
        assert key not in entries, f"Duplicate env key {key!r} in {filename}"
        entries[key] = value
    return entries


def test_long_running_app_services_load_shared_docker_env() -> None:
    for service in ("backend", "worker", "beat"):
        block = _service_block("docker-compose.yml", service)
        assert "- .env" in block
        assert "- .env.docker" in block
        assert "    environment:" not in block


def test_specialized_services_load_only_their_env_overrides() -> None:
    migrate = _service_block("docker-compose.yml", "migrate")
    assert "- .env" in migrate
    assert "- .env.docker.migrate" in migrate
    assert "- .env.docker\n" not in migrate
    assert "    environment:" not in migrate

    db_test = _service_block("docker-compose.yml", "db-test")
    assert "- .env" in db_test
    assert "- .env.docker.test" in db_test
    assert "    environment:" not in db_test


def test_development_override_does_not_duplicate_runtime_environment() -> None:
    for service in ("backend", "worker", "beat"):
        block = _service_block("docker-compose.override.yml", service)
        assert "    environment:" not in block
        assert "DATABASE_URL" not in block
        assert "VALKEY_URL" not in block


def test_docker_env_files_have_single_responsibilities() -> None:
    app_env = _env_entries(".env.docker")
    migrate_env = _env_entries(".env.docker.migrate")
    test_env = _env_entries(".env.docker.test")

    assert set(app_env) == {"DATABASE_URL", "VALKEY_URL"}
    assert set(migrate_env) == {"MIGRATION_DATABASE_URL"}
    assert test_env == {"POSTGRES_DB": "nak_planner_test"}
    assert "@db:5432/" in app_env["DATABASE_URL"]
    assert app_env["VALKEY_URL"] == "valkey://valkey:6379/0"


def test_owner_database_credentials_are_isolated_to_migration_override() -> None:
    app_env = (REPO_ROOT / ".env.docker").read_text(encoding="utf-8")
    migrate_env = (REPO_ROOT / ".env.docker.migrate").read_text(encoding="utf-8")

    assert "POSTGRES_USER" not in app_env
    assert "POSTGRES_PASSWORD" not in app_env
    assert "${POSTGRES_USER:?" in migrate_env
    assert "${POSTGRES_PASSWORD:?" in migrate_env


def test_required_database_inputs_fail_fast_during_compose_interpolation() -> None:
    app_env = _env_entries(".env.docker")
    migrate_env = _env_entries(".env.docker.migrate")

    assert "${APP_DB_USER:?" in app_env["DATABASE_URL"]
    assert "${APP_DB_PASSWORD:?" in app_env["DATABASE_URL"]
    assert "${POSTGRES_DB:?" in app_env["DATABASE_URL"]
    assert "${POSTGRES_DB:?" in migrate_env["MIGRATION_DATABASE_URL"]
