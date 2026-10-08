"""Static regression tests for the scheduler service and image tag policy (#455)."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
LONG_RUNNING = ("backend", "worker", "beat", "frontend", "db", "valkey")


def _yaml(name: str) -> dict:
    return yaml.safe_load((REPO_ROOT / name).read_text(encoding="utf-8"))


def _services() -> dict:
    return _yaml("docker-compose.yml")["services"]


def _command(service: dict) -> str:
    command = service.get("command", "")
    return command if isinstance(command, str) else " ".join(command)


def test_exactly_one_beat_scheduler_runs_with_runtime_credentials() -> None:
    services = _services()
    schedulers = [name for name, s in services.items() if " beat" in _command(s)]
    assert schedulers == ["beat"]
    for name, service in services.items():
        assert not {"-B", "--beat"} & set(_command(service).split()), name

    beat = services["beat"]
    assert "celery -A app.celery_app beat" in _command(beat)
    assert beat["env_file"] == [".env", ".env.docker"]
    assert "environment" not in beat
    assert beat["deploy"]["replicas"] == 1
    assert beat["depends_on"]["migrate"] == {"condition": "service_completed_successfully"}


def test_beat_schedule_file_is_on_a_named_volume() -> None:
    compose = _yaml("docker-compose.yml")
    beat = compose["services"]["beat"]
    schedule = _command(beat).split("--schedule", 1)[1].split()[0]
    volume, target = next(v.split(":")[:2] for v in beat["volumes"])
    assert volume in compose["volumes"]
    assert schedule.startswith(target + "/")


def test_long_running_services_restart_automatically() -> None:
    services = _services()
    for name in LONG_RUNNING:
        assert services[name].get("restart") == "unless-stopped", name
    assert services["migrate"]["restart"] == "no"


def test_test_database_is_not_part_of_the_default_stack() -> None:
    assert _services()["db-test"]["profiles"] == ["test"]


def test_image_never_syncs_dev_dependencies_at_start_and_installs_project() -> None:
    dockerfile = (REPO_ROOT / "services" / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "UV_NO_SYNC=1" in dockerfile
    assert "RUN uv sync --frozen --no-dev\n" in dockerfile


def test_main_branch_builds_do_not_publish_latest() -> None:
    build = (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    assert "value=latest" not in build
    assert "type=ref,event=branch" in build
    assert "type=sha,prefix=sha-" in build


def test_only_stable_releases_publish_latest() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    latest = [line.strip() for line in release.splitlines() if "value=latest" in line]
    assert latest == [
        "type=raw,value=latest,enable=${{ !contains(needs.release-please.outputs.tag_name, '-') }}"
    ]
