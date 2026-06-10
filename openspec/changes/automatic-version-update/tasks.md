## 1. Version Detection — Backend

- [x] 1.1 Add `APP_VERSION` to backend settings (from `importlib.metadata.version("nak-district-planner-backend")`)
- [x] 1.2 Implement `GhcrTagFetcher` that queries `https://ghcr.io/v2/{owner}/{repo}/{service}/tags/list` and parses SemVer tags
- [x] 1.3 Implement latest-version logic (sort tags by SemVer, return highest)
- [x] 1.4 Implement in-memory cache for version check results with configurable TTL
- [x] 1.5 Implement periodic Celery task `check_version` (every 6 hours) that updates the cache
- [x] 1.6 Add `GHCR_OWNER` and `GHCR_REPO` settings (defaults to GitHub repository)

## 2. Version Endpoint

- [x] 2.1 Create Pydantic schema `SystemVersionResponse` (current_version, latest_version, last_checked, release_url)
- [x] 2.2 Implement `GET /api/v1/system/version` with `?refresh=true` support
- [x] 2.3 Protect endpoint with RBAC (admin only)
- [x] 2.4 Wire the endpoint into the app router

## 3. Update Endpoint

- [x] 3.1 Add `UPDATE_MODE` setting to backend config (default: `manual`)
- [x] 3.2 Add `DOCKER_COMPOSE_DIR` setting (path to compose project directory)
- [x] 3.3 Create Pydantic schema `UpdateResponse` (status, mode, optional instructions)
- [x] 3.4 Implement `POST /api/v1/system/update` for `manual` mode (returns instructions)
- [x] 3.5 Implement `POST /api/v1/system/update` for `docker-socket` mode (enqueues Celery task)
- [x] 3.6 Implement Celery task `trigger_docker_update` that runs `docker compose pull` and `docker compose up -d`
- [x] 3.7 Ensure update task gracefully handles service restart (no hanging HTTP requests via async Celery task with subprocess timeout)
- [x] 3.8 Protect endpoint with RBAC (superadmin only)

## 4. Frontend — Pinia Store

- [x] 4.1 Create `useVersionStore` Pinia store with state: currentVersion, latestVersion, updateMode, lastChecked
- [x] 4.2 Implement `checkVersion()` action that calls `GET /api/v1/system/version`
- [x] 4.3 Implement `triggerUpdate()` action that calls `POST /api/v1/system/update`
- [x] 4.4 Implement polling on store mount (check version every 30 minutes while admin is active)

## 5. Frontend — Update Banner

- [x] 5.1 Implement `UpdateBanner.vue` component (dismissible, shows version diff, check now button, update button)
- [x] 5.2 Implement update dialog: auto-update confirmation vs. manual instructions display
- [x] 5.3 Style with Tailwind (blue info banner, proper responsive layout)
- [x] 5.4 Integrate banner into admin layout (only shown for ADMIN role)
- [x] 5.5 Implement dismiss logic (remember dismissed version in localStorage)
- [x] 5.6 Add release notes link (constructs URL from version: `https://github.com/{owner}/{repo}/releases/tag/v{version}`)

## 6. Configuration & Documentation

- [x] 6.1 Add `docker-socket` mode example to `docker-compose.override.yml` (mount `/var/run/docker.sock`)
- [x] 6.2 Add `UPDATE_MODE`, `DOCKER_COMPOSE_DIR`, `GHCR_OWNER`, `GHCR_REPO` to `.env.example`
- [x] 6.3 Document security implications of Docker socket access in project documentation

## 7. Tests

- [x] 7.1 Unit tests for SemVer parsing and latest-version selection
- [x] 7.2 Unit tests for ghcr.io response parsing (with mocked HTTP)
- [x] 7.3 Unit tests for version cache (set, get, expired, miss)
- [x] 7.4 Integration tests for `/api/v1/system/version` endpoint
- [x] 7.5 Integration tests for `/api/v1/system/update` in both modes
- [x] 7.6 Unit tests for Celery task `trigger_docker_update` (mocked subprocess)
- [x] 7.7 Unit tests for frontend `UpdateBanner.vue` component (visible/hidden for admin/non-admin, dismiss, version comparison)
