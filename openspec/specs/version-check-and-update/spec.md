# version-check-and-update Specification

## Purpose
Tells administrators that a newer release is available (GHCR tag check, SemVer 2.0 incl. prereleases) without ever executing an update; operators update via `docs/production-runbook.md`.

## Requirements

### Requirement: Periodic version check against ghcr.io
The system SHALL periodically check the GitHub Container Registry for newer Docker image tags.

#### Scenario: Scheduled version check
- **WHEN** the periodic Celery task runs
- **THEN** the system SHALL query `https://ghcr.io/v2/{owner}/{repo}/backend/tags/list` and parse SemVer tags
- **THEN** the system SHALL determine the latest available version by sorting tags per SemVer rules
- **THEN** the system SHALL cache the result in Redis with a configurable TTL (default 1 hour)

#### Scenario: No newer version found
- **WHEN** the latest available version equals the running version
- **THEN** the system SHALL cache the result and not trigger any update notification

#### Scenario: Registry unreachable
- **WHEN** the ghcr.io API is unreachable during a version check
- **THEN** the system SHALL log a warning and retain the previous cached result

### Requirement: Version information endpoint
The system SHALL expose a `GET /api/v1/system/version` endpoint returning current and latest version information.

#### Scenario: Version endpoint response
- **WHEN** an admin calls `GET /api/v1/system/version`
- **THEN** the response SHALL include `current_version` (backend), `latest_version` (from cache or null), `frontend_version` (reported by UI), `last_checked` (timestamp), and `release_url` (link to GitHub release)

#### Scenario: No cached latest version
- **WHEN** no version check has been performed yet (first startup)
- **THEN** `latest_version` SHALL be `null` and `last_checked` SHALL be `null`

#### Scenario: Force refresh
- **WHEN** the endpoint is called with `?refresh=true`
- **THEN** the system SHALL perform an immediate version check (bypass cache) and return the fresh result

### Requirement: Running version from application metadata
The system SHALL derive the running application version from package metadata.

#### Scenario: Backend version from pyproject.toml
- **WHEN** the backend starts
- **THEN** the system SHALL read the version from `importlib.metadata.version("nak-district-planner-backend")` and expose it as `current_version`

#### Scenario: Frontend version from package.json
- **WHEN** the frontend builds
- **THEN** Vite SHALL inject the version from `package.json` as `import.meta.env.PACKAGE_VERSION` (or equivalent)

### Requirement: Version cache TTL
The system SHALL cache version check results in process memory with a TTL to avoid rate limiting from ghcr.io.

#### Scenario: Cache hit
- **WHEN** the version check is within the TTL period
- **THEN** the system SHALL return the cached result without querying ghcr.io

#### Scenario: Cache miss
- **WHEN** the TTL has expired or no cache exists
- **THEN** the system SHALL query ghcr.io and update the cache

### Requirement: Admin UI update notice banner
The system SHALL display an update notification banner to administrators when the backend reports `update_available`. The banner SHALL only inform; it SHALL NOT start an update.

#### Scenario: Banner appears for admin
- **WHEN** an admin is logged in and `GET /api/v1/system/version` returns `update_available: true`
- **THEN** the system SHALL display a dismissible info banner with the newer version number, a release-notes link and the runbook commands using `docker compose -f docker-compose.yml` (build, migrate, `up -d`)

#### Scenario: Banner not shown to non-admin
- **WHEN** a non-admin user is logged in and a newer version exists
- **THEN** the system SHALL NOT display the update banner

#### Scenario: Banner dismissed
- **WHEN** an admin dismisses the banner
- **THEN** the system SHALL hide the banner until a newer version than the dismissed one is detected

#### Scenario: Banner polls while open
- **WHEN** the banner component is mounted
- **THEN** it SHALL check the version on mount and every 30 minutes until it is unmounted

### Requirement: Application SHALL NOT execute deployment updates
The application SHALL NOT pull images, rebuild, restart services or run migrations on
its own. It SHALL NOT expose an endpoint, background task, setting or UI control that
triggers a deployment update, and SHALL NOT require a mounted Docker socket.

#### Scenario: Update endpoint is absent
- **WHEN** any client calls `POST /api/v1/system/update`
- **THEN** the API responds with 404 or 405 and no update is started

### Requirement: Version comparison SHALL follow SemVer 2.0 including prereleases
The version check SHALL parse SemVer tags with prerelease identifiers, normalize PEP 440
pre-release versions (`1.0.0rc1` → `1.0.0-rc.1`, `a` → `alpha`, `b` → `beta`), apply
SemVer 2.0 precedence and ignore non-SemVer tags. `update_available` SHALL be true only
if the latest version is strictly newer than the running version.

#### Scenario: Prerelease precedence
- **WHEN** comparing `1.0.0-rc.1`, `1.0.0-rc.2` and `1.0.0`
- **THEN** `1.0.0-rc.1` < `1.0.0-rc.2` < `1.0.0`

#### Scenario: PEP 440 runtime version
- **WHEN** the running version is `1.0.0rc1` and the latest tag is `1.0.0-rc.1`
- **THEN** both are equal and `update_available` is false

#### Scenario: Never offer a downgrade
- **WHEN** the running version is `1.0.0rc1` and the registry contains `0.29.3`
- **THEN** `update_available` is false

### Requirement: Prereleases SHALL only be offered on a prerelease line
Prerelease tags SHALL be considered only when the running version is itself a
prerelease; installations on a stable release SHALL only be offered stable releases.

#### Scenario: Stable 0.x is not offered a release candidate
- **WHEN** the running version is `0.29.3` and the registry contains `1.0.0-rc.1`
- **THEN** no update is offered

#### Scenario: Stable 1.0.0 is not offered 1.1.0-rc.1
- **WHEN** the running version is `1.0.0` and the registry contains `1.1.0-rc.1`
- **THEN** no update is offered

#### Scenario: Release candidate line receives newer candidates and the final release
- **WHEN** the running version is `1.0.0rc1` and the registry contains `1.0.0-rc.2`
- **THEN** `1.0.0-rc.2` is offered, and once `1.0.0` exists, `1.0.0` is offered
