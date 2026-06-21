## 1. Version Detection — Backend

- [ ] 1.1 Add `APP_VERSION` to backend settings (from `importlib.metadata.version("nak-district-planner-backend")`)
- [ ] 1.2 Implement `GhcrTagFetcher` that queries `https://ghcr.io/v2/{owner}/{repo}/{service}/tags/list` and parses SemVer tags
- [ ] 1.3 Implement latest-version logic (sort tags by SemVer, return highest)
- [ ] 1.4 Implement Redis-based cache for version check results with configurable TTL
- [ ] 1.5 Implement periodic Celery task `check_version` (every 6 hours) that updates the cache
- [ ] 1.6 Add `GHCR_OWNER` and `GHCR_REPO` settings (defaults to GitHub repository)

## 2. Version Endpoint

- [ ] 2.1 Create Pydantic schema `SystemVersionResponse` (current_version, latest_version, frontend_version, last_checked, release_url)
- [ ] 2.2 Implement `GET /api/v1/system/version` with `?refresh=true` support
- [ ] 2.3 Protect endpoint with RBAC (admin only)
- [ ] 2.4 Wire the endpoint into the app router

## 3. Update Endpoint

- [ ] 3.1 Add `UPDATE_MODE` setting to backend config (default: `manual`)
- [ ] 3.2 Add `DOCKER_COMPOSE_DIR` setting (path to compose project directory)
- [ ] 3.3 Create Pydantic schema `UpdateResponse` (status, mode, optional instructions)
- [ ] 3.4 Implement `POST /api/v1/system/update` for `manual` mode (returns instructions)
- [ ] 3.5 Implement `POST /api/v1/system/update` for `docker-socket` mode (enqueues Celery task)
- [ ] 3.6 Implement Celery task `trigger_docker_update` that runs `docker compose pull` and `docker compose up -d`
- [ ] 3.7 Ensure update task gracefully handles service restart (no hanging HTTP requests)
- [ ] 3.8 Protect endpoint with RBAC (admin only)

## 4. Frontend — Pinia Store

- [ ] 4.1 Create `useVersionStore` Pinia store with state: currentVersion, latestVersion, updateMode, lastChecked
- [ ] 4.2 Implement `checkVersion()` action that calls `GET /api/v1/system/version`
- [ ] 4.3 Implement `triggerUpdate()` action that calls `POST /api/v1/system/update`
- [ ] 4.4 Implement polling on store mount (check version every 30 minutes while admin is active)

## 5. Frontend — Update Banner

- [ ] 5.1 Implement `UpdateBanner.vue` component (dismissible, shows version diff, check now button, update button)
- [ ] 5.2 Implement update dialog: auto-update confirmation vs. manual instructions display
- [ ] 5.3 Style with Tailwind (blue info banner, proper responsive layout)
- [ ] 5.4 Integrate banner into admin layout (only shown for ADMIN role)
- [ ] 5.5 Implement dismiss logic (remember dismissed version in localStorage)
- [ ] 5.6 Add release notes link (constructs URL from version: `https://github.com/{owner}/{repo}/releases/tag/v{version}`)

## 6. Configuration & Documentation

- [ ] 6.1 Add `docker-socket` mode example to `docker-compose.override.yml` (mount `/var/run/docker.sock`)
- [ ] 6.2 Add `UPDATE_MODE`, `DOCKER_COMPOSE_DIR`, `GHCR_OWNER`, `GHCR_REPO` to `.env.example`
- [ ] 6.3 Document security implications of Docker socket access in project documentation

## 7. Tests

- [ ] 7.1 Unit tests for SemVer parsing and latest-version selection
- [ ] 7.2 Unit tests for ghcr.io response parsing (with mocked HTTP)
- [ ] 7.3 Unit tests for version cache (set, get, expired, miss)
- [ ] 7.4 Unit tests for `/api/v1/system/version` endpoint
- [ ] 7.5 Unit tests for `/api/v1/system/update` in both modes
- [ ] 7.6 Unit tests for Celery task `trigger_docker_update` (mocked subprocess)
- [ ] 7.7 Unit tests for frontend `UpdateBanner.vue` component (visible/hidden for admin/non-admin, dismiss, version comparison)
