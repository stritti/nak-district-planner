## Why

The in-app update (`POST /api/v1/system/update`, Celery task `trigger_docker_update`,
`UPDATE_MODE=docker-socket`) was unsafe and did not work (#469): it ran
`docker compose pull`/`up -d` without `-f docker-compose.yml`, so on a production
checkout the dev override applied (ports 8000/5432/6379 on 0.0.0.0, `--reload`,
source mounts); app services use `build:` so `pull` never updated the app; there was
no migration step; the image has no docker CLI; and a mounted socket is host root.
In addition, the version compare ignored prerelease tags and the PEP 440 runtime
version (`1.0.0rc1`), so a 1.0 release candidate saw an "update" to an older 0.x.

## What Changes

- **BREAKING** Remove `POST /api/v1/system/update`, the `trigger_docker_update` task,
  `UPDATE_MODE`/`DOCKER_COMPOSE_DIR` settings and the docker-socket compose example.
- Remove the "Aktualisieren" trigger from `UpdateBanner.vue`; keep the banner with the
  release-notes link and the runbook commands (`docker compose -f docker-compose.yml …`).
- SemVer 2.0 compare incl. prereleases; PEP 440 pre-release normalization
  (`1.0.0rc1` → `1.0.0-rc.1`); non-SemVer tags ignored.
- Prerelease policy: prereleases are offered only when the running version is itself
  a prerelease. `GET /api/v1/system/version` returns `update_available` (strictly newer).
- Supersedes the update-execution parts of `automatic-version-update`.

## Capabilities

### New Capabilities
- *(none)*

### Modified Capabilities
- `version-check-and-update` (baseline from `automatic-version-update`): removes the
  update endpoint and `UPDATE_MODE`, makes the banner display-only, corrects the cache
  requirement (in-memory TTL) and adds SemVer/prerelease rules.

## Impact

- Backend: `routers/system.py`, `schemas/system.py`, `version_check/ghcr.py`, `tasks.py`, `config.py`
- Frontend: `api/system.ts`, `stores/version.ts`, `components/UpdateBanner.vue`
- Config/Docs: `docker-compose.override.yml`, `.env.example`, `docs/security-baseline.md`,
  `docs/production-runbook.md`, `docs/architecture-status.md`, `docs/rbac-coverage.md`
