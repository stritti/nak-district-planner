# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

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


def test_branch_and_pr_builds_never_publish_images() -> None:
    build = _yaml(".github/workflows/build.yml")
    assert build["permissions"].get("packages") != "write"
    image_builds = []
    for job in build["jobs"].values():
        assert job.get("permissions", {}).get("packages") != "write"
        for step in job.get("steps", []):
            action = step.get("uses", "")
            assert not action.startswith("docker/login-action@")
            if action.startswith("docker/build-push-action@"):
                image_builds.append(step)
                assert step["with"]["push"] is False
                assert "tags" not in step["with"]
    assert len(image_builds) == 2


def test_release_please_creates_draft_and_tag_before_building() -> None:
    import json

    config = json.loads((REPO_ROOT / "release-please-config.json").read_text(encoding="utf-8"))
    assert config["draft"] is True
    assert config["force-tag-creation"] is True

    release = _yaml(".github/workflows/release.yml")
    assert release["concurrency"]["cancel-in-progress"] is False
    assert release["concurrency"]["group"] == "release-publication"
    assert release["permissions"]["contents"] == "read"


def test_release_requires_verified_notes_and_both_images() -> None:
    release = _yaml(".github/workflows/release.yml")
    notes = release["jobs"]["publish-upgrade-notes"]
    assert notes["needs"] == "release-please"
    assert "always()" in notes["if"]
    assert "workflow_dispatch" in notes["if"]
    assert notes["permissions"]["contents"] == "write"

    note_steps = notes["steps"]
    checkout = next(s for s in note_steps if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["fetch-tags"] is True
    assert "inputs.release_tag || needs.release-please.outputs.tag_name" in checkout["with"]["ref"]
    verify = next(s for s in note_steps if s.get("id") == "verify")
    assert "git merge-base --is-ancestor HEAD origin/main" in verify["run"]
    assert "gh release view" in verify["run"]
    assert "isDraft" in verify["run"]
    assert any("scripts/publish_release_upgrade_notes.py" in s.get("run", "") for s in note_steps)
    notes_script = (REPO_ROOT / "scripts/publish_release_upgrade_notes.py").read_text(encoding="utf-8")
    assert "verify_previous_release_is_published(repo, tag)" in notes_script

    build = release["jobs"]["docker-build"]
    assert build["needs"] == "publish-upgrade-notes"
    assert build["if"] == "${{ always() && needs.publish-upgrade-notes.result == 'success' }}"
    steps = build["steps"]
    actions = [s for s in steps if s.get("uses", "").startswith("docker/build-push-action@")]
    assert [s["id"] for s in actions] == ["backend", "frontend"]
    for service, action in zip(("backend", "frontend"), actions, strict=True):
        assert action["with"]["push"] is True
        assert action["with"]["context"] == f"services/{service}"
        assert f"/{service}:candidate-" in action["with"]["tags"]
        assert "github.run_id" in action["with"]["tags"]
        assert "github.run_attempt" in action["with"]["tags"]
        assert "latest" not in action["with"]["tags"]
    candidate = next(s for s in steps if s.get("id") == "candidate")
    assert "scripts/release_candidate_manifest.py check" in candidate["run"]
    for action in actions:
        assert action["if"] == "${{ steps.candidate.outputs.reuse != 'true' }}"
    saved = next(s for s in steps if s.get("id") == "saved")
    assert saved["if"] == "${{ steps.candidate.outputs.reuse != 'true' }}"
    assert "scripts/release_candidate_manifest.py save" in saved["run"]
    promote = next(s for s in steps if "scripts/promote_release_images.py" in s.get("run", ""))
    assert promote["env"]["BACKEND_DIGEST"] == "${{ steps.candidate.outputs.backend_digest || steps.saved.outputs.backend_digest }}"
    assert promote["env"]["FRONTEND_DIGEST"] == "${{ steps.candidate.outputs.frontend_digest || steps.saved.outputs.frontend_digest }}"
    assert promote["env"]["RELEASE_TAG"] == "${{ needs.publish-upgrade-notes.outputs.tag_name }}"


def test_failed_notes_cannot_publish_images() -> None:
    release = _yaml(".github/workflows/release.yml")
    notes = release["jobs"]["publish-upgrade-notes"]
    build = release["jobs"]["docker-build"]
    assert build["needs"] == "publish-upgrade-notes"
    assert build["if"] == "${{ always() && needs.publish-upgrade-notes.result == 'success' }}"
    assert any("scripts/publish_release_upgrade_notes.py" in s.get("run", "") for s in notes["steps"])


def test_only_promotion_script_can_mutate_release_aliases() -> None:
    release = (REPO_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "docker/metadata-action@" not in release
    assert "value=latest" not in release
    assert "scripts/promote_release_images.py" in release
    promoter = (REPO_ROOT / "scripts/promote_release_images.py").read_text(encoding="utf-8")
    assert "self.ensure_version_tags()" in promoter
    assert "self.verify_staging()" in promoter
    assert "self.ensure_not_superseded()" in promoter
    assert "self.tag_image(repo, alias, image.digest)" in promoter
    assert 'command("gh", "release", "edit", self.tag, "--draft=false")' in promoter
