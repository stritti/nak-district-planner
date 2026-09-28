## 1. Version Detection — Backend

- [x] 1.1 Add `APP_VERSION` to backend settings (from `importlib.metadata.version("nak-district-planner-backend")`) *(in `app/config.py`)*
- [x] 1.2 Implement `GhcrTagFetcher` that queries `https://ghcr.io/v2/{owner}/{repo}/{service}/tags/list` and parses SemVer tags *(`adapters/version_check/ghcr.py`)*
- [x] 1.3 Implement latest-version logic (sort tags by SemVer, return highest) *(`adapters/version_check/ghcr.py::latest_semver`)*
- [x] 1.4 Implement Redis-based cache for version check results with configurable TTL *(`adapters/version_check/cache.py`)*
- [x] 1.5 Implement periodic Celery task `check_version` (every 6 hours) that updates the cache *(Beat-Schedule in `celery_app.py`, Task in `application/tasks.py`)*
- [x] 1.6 Add `GHCR_OWNER` and `GHCR_REPO` settings (defaults to GitHub repository) *(in `app/config.py` + `.env.example`)*

## 2. Version Endpoint

- [x] 2.1 Create Pydantic schema `SystemVersionResponse` (current_version, latest_version, frontend_version, last_checked, release_url) *(`adapters/api/schemas/system.py`)*
- [x] 2.2 Implement `GET /api/v1/system/version` with `?refresh=true` support *(`routers/system.py`, inkl. `?refresh=true`)*
- [x] 2.3 Protect endpoint with RBAC (admin only) *(SUPERADMIN-Guard)*
- [x] 2.4 Wire the endpoint into the app router *(in `main.py` registriert)*

## 3. Update Endpoint

- [x] 3.1 Add `UPDATE_MODE` setting to backend config (default: `manual`) *(default `manual`)*
- [x] 3.2 Add `DOCKER_COMPOSE_DIR` setting (path to compose project directory) *(in `app/config.py`)*
- [x] 3.3 Create Pydantic schema `UpdateResponse` (status, mode, optional instructions) *(`adapters/api/schemas/system.py`)*
- [x] 3.4 Implement `POST /api/v1/system/update` for `manual` mode (returns instructions) *(liefert Anweisungen im `manual`-Modus)*
- [x] 3.5 Implement `POST /api/v1/system/update` for `docker-socket` mode (enqueues Celery task) *(enqueued `trigger_docker_update`)*
- [x] 3.6 Implement Celery task `trigger_docker_update` that runs `docker compose pull` and `docker compose up -d` *(`application/tasks.py::trigger_docker_update`)*
- [x] 3.7 Ensure update task gracefully handles service restart (no hanging HTTP requests) *(Task ist entkoppelt vom HTTP-Request)*
- [x] 3.8 Protect endpoint with RBAC (admin only) *(SUPERADMIN-Guard)*

## 4. Frontend — Pinia Store

- [x] 4.1 Create `useVersionStore` Pinia store with state: currentVersion, latestVersion, updateMode, lastChecked *(`src/stores/version.ts`)*
- [x] 4.2 Implement `checkVersion()` action that calls `GET /api/v1/system/version` *(über `src/api/system.ts`)*
- [x] 4.3 Implement `triggerUpdate()` action that calls `POST /api/v1/system/update` *(über `src/api/system.ts`)*
- [ ] 4.4 Implement polling on store mount (check version every 30 minutes while admin is active) *(kein Polling im `version.ts`-Store gefunden — prüfen, ob ein anderer Timer existiert)*

## 5. Frontend — Update Banner

- [x] 5.1 Implement `UpdateBanner.vue` component (dismissible, shows version diff, check now button, update button) *(`src/components/UpdateBanner.vue`)*
- [x] 5.2 Implement update dialog: auto-update confirmation vs. manual instructions display *(in `UpdateBanner.vue` bzw. Store)*
- [x] 5.3 Style with Tailwind (blue info banner, proper responsive layout) *(Tailwind-Klassen umgesetzt)*
- [x] 5.4 Integrate banner into admin layout (only shown for ADMIN role) *(nur für Admin-Rolle sichtbar)*
- [x] 5.5 Implement dismiss logic (remember dismissed version in localStorage) *(localStorage)*
- [x] 5.6 Add release notes link (constructs URL from version: `https://github.com/{owner}/{repo}/releases/tag/v{version}`) *(Release-Notes-Link im Banner)*

## 6. Configuration & Documentation

- [x] 6.1 Add `docker-socket` mode example to `docker-compose.override.yml` (mount `/var/run/docker.sock`) *(in `docker-compose.override.yml`)*
- [x] 6.2 Add `UPDATE_MODE`, `DOCKER_COMPOSE_DIR`, `GHCR_OWNER`, `GHCR_REPO` to `.env.example` *(Einträge vorhanden)*
- [x] 6.3 Document security implications of Docker socket access in project documentation

## 7. Tests

- [x] 7.1 Unit tests for SemVer parsing and latest-version selection *(`tests/unit/test_version_check.py`)*
- [x] 7.2 Unit tests for ghcr.io response parsing (with mocked HTTP) *(in `test_version_check.py`)*
- [x] 7.3 Unit tests for version cache (set, get, expired, miss) *(Cache-Tests)*
- [x] 7.4 Unit tests for `/api/v1/system/version` endpoint *(`tests/integration/test_version_endpoint.py`)*
- [x] 7.5 Unit tests for `/api/v1/system/update` in both modes *(Update-Endpoint-Tests)*
- [x] 7.6 Unit tests for Celery task `trigger_docker_update` (mocked subprocess) *(`tests/unit/test_tasks_more.py`)*
- [x] 7.7 Unit tests for frontend `UpdateBanner.vue` component (visible/hidden for admin/non-admin, dismiss, version comparison) *(`src/components/__tests__/UpdateBanner.test.ts` + `src/stores/version.test.ts`)*
