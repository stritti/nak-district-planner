## 1. Remove update execution

- [x] 1.1 Remove `POST /api/v1/system/update` and `UpdateResponse` schema
- [x] 1.2 Remove Celery task `trigger_docker_update`
- [x] 1.3 Remove `UPDATE_MODE` / `DOCKER_COMPOSE_DIR` settings, `.env.example` entries and docker-socket example in `docker-compose.override.yml`
- [x] 1.4 Remove update trigger UI (`triggerUpdate`, store `trigger()`, "Aktualisieren" button); keep banner + release notes + runbook commands
- [x] 1.5 Update security baseline, runbook, architecture status and RBAC coverage docs

## 2. Version compare

- [x] 2.1 Parse SemVer incl. prerelease; normalize PEP 440 pre-releases (`a`/`b`/`rc`)
- [x] 2.2 SemVer 2.0 precedence (numeric identifiers numerically, final > prerelease)
- [x] 2.3 Offer prereleases only to installations running a prerelease
- [x] 2.4 Return `update_available` from `GET /api/v1/system/version`; frontend uses it

## 3. Tests

- [x] 3.1 Unit: `1.0.0-rc.1 < 1.0.0-rc.2 < 1.0.0`, `1.0.0rc1 == 1.0.0-rc.1`, rc not offered to 0.x, `1.0.0` not offered `1.1.0-rc.1`, never a downgrade
- [x] 3.2 Integration: update endpoint absent; RC install not offered older 0.x
- [x] 3.3 Frontend: no trigger button, runbook commands pinned to `docker-compose.yml`
