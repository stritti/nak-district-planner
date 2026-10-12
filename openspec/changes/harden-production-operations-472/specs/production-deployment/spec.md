## ADDED Requirements

### Requirement: Build contexts exclude local secrets and artifacts
The frontend and backend Docker build contexts SHALL exclude local `.env*` files, development dependency directories, coverage artifacts and VCS metadata.

#### Scenario: Frontend or backend image is assembled
- **WHEN** Docker creates the build context
- **THEN** local secrets and build artifacts are excluded from the context

### Requirement: Public frontend is served by an unprivileged container
The frontend SHALL use a version-pinned unprivileged Nginx image listening on internal port 8080. The frontend SHALL prevent caching of `index.html` and `sw.js`, suppress version headers, and preserve the proxy and security-header behavior.

#### Scenario: Production TLS proxy forwards a browser request
- **WHEN** the request reaches the frontend from either bundled or external Traefik
- **THEN** it connects to port 8080 and the non-root process serves the SPA

#### Scenario: Browser reloads the application shell or service worker
- **WHEN** `/index.html` or `/sw.js` is requested
- **THEN** the response prevents stale caching without dropping the baseline security headers

### Requirement: Production application containers enforce least privilege
The frontend, backend, worker, beat and migrate services SHALL have read-only root filesystems, no added Linux capabilities, no-new-privileges, explicit writable temporary or state mounts, and bounded memory/PID resources. Worker and cache health SHALL be checked before dependent services run.

#### Scenario: The production stack starts
- **WHEN** Docker Compose resolves the runtime application services
- **THEN** their hardening settings and healthchecks are present
- **AND** the beat schedule remains writable on its dedicated persistent volume

### Requirement: Valkey is authenticated and production runtime secrets are non-default
Valkey SHALL require VALKEY_PASSWORD for its server, healthcheck and application/Celery clients. Production SHALL reject missing, default or URI-unsafe VALKEY_PASSWORD and missing or default APP_DB_PASSWORD. Runtime services SHALL NOT receive database owner credentials. Compose SHALL expand VALKEY_PASSWORD as a quoted container environment variable, never as interpolated shell code.
#### Scenario: Operator forgets or uses development secrets
- **WHEN** application startup uses a missing or placeholder runtime credential
- **THEN** production_guard blocks startup

#### Scenario: Valkey starts
- **WHEN** a client connects without the configured password
- **THEN** Valkey refuses authenticated operations

#### Scenario: Runtime password contains URL-reserved characters
- **WHEN** production startup receives a VALKEY_PASSWORD that cannot be embedded directly in a URI
- **THEN** startup fails with a clear validation error

#### Scenario: Compose starts Valkey and runs the healthcheck
- **WHEN** VALKEY_PASSWORD contains characters that have shell syntax
- **THEN** the literal value is delivered as a single credential argument to Valkey
- **AND** the healthcheck authenticates with that exact value without interpreting it as code

### Requirement: Standalone identity providers require secure configuration
The standalone Keycloak and Authentik Compose examples SHALL require operator-provided passwords and HTTPS public hostnames. Insecure cookie overrides, hardcoded personal domains and deprecated Compose version declarations SHALL NOT remain.

#### Scenario: Required secrets are missing
- **WHEN** standalone IdP Compose is rendered without configured secrets
- **THEN** interpolation fails instead of deploying known placeholder credentials

### Requirement: Disaster recovery verifies global roles and migrated security controls
Production database backups SHALL include separately encrypted global role definitions without password hashes. The isolated Restore Drill SHALL migrate the source using the current Alembic head, restore the role archive before the database archive, verify RLS policies, `SECURITY DEFINER` functions, grants and the application role, and reject corrupt archives without changing restored data.

#### Scenario: Weekly restore drill completes
- **WHEN** an encrypted backup is restored in a fresh independent PostgreSQL cluster
- **THEN** data, role permissions, RLS and defined functions match the required application security invariants

#### Scenario: Damaged backup is provided
- **WHEN** a truncated archive is used for a dry-run restore
- **THEN** validation fails and the restored data remain unchanged

### Requirement: Production upgrade actions are prominent in published Release Notes
Changes that require an operator to modify an existing production installation SHALL introduce an actionable, release-specific upgrade note alongside the change. Following release-please publication, the release workflow SHALL prepend newly introduced upgrade notes under a prominent "WICHTIG: Anpassungen bei produktiven Installationen" heading before the generated changelog. The release image publication SHALL depend on successful upgrade-note processing.

#### Scenario: Release includes a new required environment variable
- **WHEN** a version includes a new production upgrade note with affected deployments, pre-upgrade steps and post-upgrade checks
- **THEN** its GitHub Release description begins with the upgrade instructions
- **AND** the original generated changelog remains intact below those instructions

#### Scenario: Subsequent release has no new required operator actions
- **WHEN** a later release only contains older upgrade notes or no upgrade notes
- **THEN** the GitHub Release description stays unchanged
- **AND** older operator actions are not repeated

#### Scenario: Upgrade note publication fails
- **WHEN** a new upgrade note lacks affected deployments, pre-upgrade steps or post-upgrade checks, or GitHub rejects the release-description update
- **THEN** the publish-upgrade-notes job fails
- **AND** the release image publishing job does not run

#### Scenario: Upgrade notes publication is retried
- **WHEN** the release description already includes the note marker for the same release
- **THEN** the release publisher leaves it unchanged instead of duplicating the notice
