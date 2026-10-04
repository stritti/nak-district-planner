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


def test_runtime_services_wait_for_one_shot_migration() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    migrate = services["migrate"]
    assert migrate["command"] == "uv run alembic upgrade head"
    assert migrate["restart"] == "no"
    assert ".env.docker.migrate" in migrate["env_file"]

    for service_name in ("backend", "worker"):
        dependency = services[service_name]["depends_on"]["migrate"]
        assert dependency["condition"] == "service_completed_successfully"
        assert ".env.docker.migrate" not in services[service_name]["env_file"]