## ADDED Requirements

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

### Requirement: Admin-only update endpoint
The system SHALL provide a `POST /api/v1/system/update` endpoint that triggers a system update, restricted to users with the `ADMIN` role.

#### Scenario: Update in docker-socket mode
- **WHEN** `UPDATE_MODE=docker-socket` and an admin calls `POST /api/v1/system/update`
- **THEN** the system SHALL enqueue a Celery task that runs `docker compose pull` and `docker compose up -d` for backend, worker, and frontend services
- **THEN** the endpoint SHALL immediately return `{"status": "started", "mode": "docker-socket"}`

#### Scenario: Update in manual mode
- **WHEN** `UPDATE_MODE=manual` and an admin calls `POST /api/v1/system/update`
- **THEN** the system SHALL return `{"status": "manual", "instructions": ["command1", "command2", ...]}` with the exact commands to execute

#### Scenario: Non-admin cannot trigger update
- **WHEN** a non-admin user calls `POST /api/v1/system/update`
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Admin UI update banner
The system SHALL display an update notification banner to administrators when a newer version is available.

#### Scenario: Banner appears for admin
- **WHEN** an admin is logged in and `latest_version > current_version`
- **THEN** the system SHALL display a dismissible info banner at the top of the page with the newer version number

#### Scenario: Banner not shown to non-admin
- **WHEN** a non-admin user is logged in and a newer version exists
- **THEN** the system SHALL NOT display the update banner

#### Scenario: Banner dismissed
- **WHEN** an admin dismisses the banner
- **THEN** the system SHALL hide the banner until a newer version than the dismissed one is detected

#### Scenario: Update button triggers flow
- **WHEN** an admin clicks the update button in the banner
- **THEN** the system SHALL call `POST /api/v1/system/update`
- **THEN** the UI SHALL display the result (progress indicator or manual instructions)

### Requirement: Running version from application metadata
The system SHALL derive the running application version from package metadata.

#### Scenario: Backend version from pyproject.toml
- **WHEN** the backend starts
- **THEN** the system SHALL read the version from `importlib.metadata.version("nak-district-planner-backend")` and expose it as `current_version`

#### Scenario: Frontend version from package.json
- **WHEN** the frontend builds
- **THEN** Vite SHALL inject the version from `package.json` as `import.meta.env.PACKAGE_VERSION` (or equivalent)

### Requirement: Update mode configuration
The system SHALL support two update modes controlled by an environment variable.

#### Scenario: docker-socket mode configured
- **WHEN** `UPDATE_MODE=docker-socket` is set in the environment
- **THEN** the system SHALL enable the automatic update subprocess execution

#### Scenario: manual mode (default)
- **WHEN** `UPDATE_MODE` is not set or set to `manual`
- **THEN** the system SHALL only display manual update instructions

### Requirement: Version cache TTL
The system SHALL cache version check results in Redis to avoid rate limiting from ghcr.io.

#### Scenario: Cache hit
- **WHEN** the version check is within the TTL period
- **THEN** the system SHALL return the cached result without querying ghcr.io

#### Scenario: Cache miss
- **WHEN** the TTL has expired or no cache exists
- **THEN** the system SHALL query ghcr.io and update the cache
