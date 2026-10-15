# production-deployment Specification

## Purpose

Describes the production runtime contract: the Docker Compose stack (backend, worker, frontend, db, valkey and the one-shot `migrate` tool service), the HTTP boundary behind an external TLS reverse proxy, health checks and backup/restore.

## Requirements

### Requirement: Container builds are reproducible
Production container builds SHALL install application dependencies from the committed lockfiles in frozen mode (`uv sync --frozen`, `bun install --frozen-lockfile`) and SHALL use versioned Python and Bun build images.

#### Scenario: Frontend image is built
- **WHEN** the frontend Docker image installs JavaScript dependencies
- **THEN** Bun uses the committed lockfile in frozen mode

### Requirement: Internal HTTP cannot bypass the public TLS boundary
The default production Compose configuration SHALL NOT publish the internal HTTP frontend service on all host interfaces. Public traffic SHALL enter through the configured TLS reverse proxy.

#### Scenario: Default Compose stack starts
- **WHEN** the frontend nginx is published to the host
- **THEN** it is bound to the loopback interface only

### Requirement: Browser security headers are applied
The application nginx SHALL emit a restrictive Content-Security-Policy (`connect-src 'self'`, `object-src 'none'`), `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`. HSTS SHALL be configured at the public TLS termination layer, not on the internal HTTP hop.

#### Scenario: SPA response
- **WHEN** the frontend serves the application
- **THEN** the response carries the Content-Security-Policy and baseline security headers

### Requirement: Explicit migrations with owner credentials
Database migrations SHALL run only through the `migrate` service (`alembic upgrade head`) with owner credentials from `.env.docker.migrate`; long-running services SHALL use the application role.

#### Scenario: Deployment
- **WHEN** a new release is deployed
- **THEN** the operator runs `docker compose run --no-deps --rm migrate` before restarting services

### Requirement: Health endpoint
`GET /health` and `GET /api/health` SHALL report database and Valkey connectivity and respond with 503 when a dependency is unavailable; the backend container healthcheck SHALL use it.

#### Scenario: Database down
- **WHEN** the database is unreachable
- **THEN** `/health` responds with 503

### Requirement: Backup and restore
Operators SHALL have `scripts/backup.sh` (encrypted `pg_dump`) and `scripts/restore.sh`; the weekly `Restore Drill` workflow SHALL prove an encrypted backup restores into an isolated database.

#### Scenario: Weekly drill
- **WHEN** the scheduled restore drill runs
- **THEN** it fails if the backup cannot be restored and verified

### Requirement: Database migrations run before runtime services
Schema-changing migrations SHALL execute as a dedicated one-shot deployment step with migration credentials. API and worker processes SHALL NOT execute Alembic upgrades during application startup. Concurrent migration runs SHALL serialize on a PostgreSQL advisory lock. The API and worker runtimes SHALL fail fast when the deployed database revision does not match the Alembic head shipped with the application, without applying DDL itself.

#### Scenario: Normal stack startup
- **WHEN** the Compose stack is started
- **THEN** the migration service waits for a healthy database
- **AND** applies `alembic upgrade head`
- **AND** backend and worker start only after migration completion succeeds

#### Scenario: Migration fails
- **WHEN** the migration service exits unsuccessfully
- **THEN** backend and worker do not start

#### Scenario: Concurrent migration runs
- **WHEN** a second migration run starts while another one holds the migration advisory lock
- **THEN** it waits until the first run releases the lock
- **AND** only then applies any remaining revisions

#### Scenario: Runtime starts against a stale schema
- **WHEN** the API process or the Celery worker starts and `alembic_version` does not match the Alembic head shipped with the application
- **THEN** startup fails before request processing begins
- **AND** the runtime does not apply a migration automatically

#### Scenario: Schema version cannot be read
- **WHEN** the API process cannot read `alembic_version`
- **THEN** startup fails with a schema-version error
- **AND** operators are directed to run the deployment migration step

#### Scenario: Database unreachable at worker start
- **WHEN** a Celery worker or beat process starts and the database connection is refused, the host does not resolve or the connection times out
- **THEN** the schema check fails with a schema-version error and the process exits instead of continuing without the check

### Requirement: Runtime credentials cannot perform deployment DDL
Backend, worker and every other runtime service SHALL load only runtime database credentials. The PostgreSQL owner password SHALL live in a dedicated env file loaded only by the database containers and the migration service.

#### Scenario: Runtime services are configured
- **WHEN** Docker Compose resolves any service other than `db`, `db-test`, `migrate` and `valkey`
- **THEN** the service SHALL NOT load `.env.db` or `.env.docker.migrate`
- **AND** its environment SHALL NOT contain `POSTGRES_PASSWORD` or `MIGRATION_DATABASE_URL`

#### Scenario: Owner password file is missing
- **WHEN** `.env.db` does not exist
- **THEN** Docker Compose fails while loading the configuration instead of starting services without it

### Requirement: Migration operations are documented
The repository SHALL document the explicit production and local-development migration commands, including the one-shot Compose service, the fail-fast runtime schema check and its effect on rollbacks.

#### Scenario: Operator deploys a release
- **WHEN** an operator follows `docs/production-runbook.md`
- **THEN** the migration step is `docker compose -f docker-compose.yml run --no-deps --rm migrate` without an appended Alembic command
- **AND** the runbook matches `docs/deployment-migrations.md`

#### Scenario: Operator rolls back to an older image
- **WHEN** an older image is started against a schema migrated by a newer release
- **THEN** the documentation states that the runtime fails closed with a schema-version error
- **AND** names backup restore or an explicit downgrade with the newer image as the remedy

#### Scenario: Developer migrates locally
- **WHEN** a developer runs `make migrate` or migrates from the host
- **THEN** `make migrate` uses the one-shot `migrate` service, which reads the owner password from `.env.db`
- **AND** the host command sets `MIGRATION_DATABASE_URL` with the owner password from `.env.db` instead of relying on the example `DATABASE_URL`

### Requirement: A single scheduler runs periodic jobs
The Compose stack SHALL run exactly one Celery beat process as a dedicated service. It SHALL use runtime database credentials only, start after the one-shot migration completed successfully, verify the schema revision before scheduling, and persist its schedule file on a named volume.

#### Scenario: Stack starts
- **WHEN** the Compose stack is started
- **THEN** the `beat` service starts after `migrate` completed successfully
- **AND** loads only `.env` and `.env.docker`
- **AND** stores its schedule under the `beat_schedule` volume

#### Scenario: Schema is stale
- **WHEN** beat starts and `alembic_version` does not match the shipped head
- **THEN** beat exits with a non-zero status without sending tasks

#### Scenario: Worker command
- **WHEN** Docker Compose resolves any service other than `beat`
- **THEN** its command SHALL NOT embed a beat scheduler (`-B`/`--beat`)

### Requirement: Celery storage exists without runtime DDL
The migration step SHALL create the Celery broker and result tables and grant the runtime role DML and sequence usage, so worker and beat never need DDL rights.

#### Scenario: Fresh database
- **WHEN** worker and beat start as the runtime role against a freshly migrated database
- **THEN** they can enqueue, consume and record tasks
- **AND** the runtime role still has no CREATE privilege on schema `public`

### Requirement: Long-running services restart automatically
Long-running services SHALL use `restart: unless-stopped`; the one-shot migration SHALL NOT restart; the test database SHALL only start with the `test` profile.

#### Scenario: Host reboot
- **WHEN** the Docker daemon restarts
- **THEN** backend, worker, beat, frontend, db and valkey come back up
- **AND** `migrate` and `db-test` do not

### Requirement: Runtime images never sync dependencies at start
The backend image SHALL contain the installed project without the dev dependency group, and container commands SHALL NOT synchronize dependencies at start.

#### Scenario: Container start
- **WHEN** a backend, worker, beat or migrate container starts with a `uv run` command
- **THEN** no packages are downloaded or installed
- **AND** the reported application version equals the project version

### Requirement: `latest` is reserved for stable releases
Branch builds SHALL publish only branch and commit-SHA image tags. Only the release workflow SHALL publish `latest`, and only for non-prerelease versions.

#### Scenario: Push to main
- **WHEN** a commit is pushed to `main`
- **THEN** images are tagged `main` and `sha-<sha>`
- **AND** `latest` is not changed

#### Scenario: Stable release
- **WHEN** release-please creates a release without a prerelease suffix
- **THEN** the release workflow tags the images with the version and `latest`

### Requirement: Reliable Celery transport
The Celery worker and Beat SHALL use the application's Valkey URL as a Redis-protocol broker and result backend, with JSON serialization and a prefetch multiplier of one. Only the retry-safe calendar sync task SHALL use late acknowledgements and a 240-second soft / 300-second hard time limit; non-idempotent mail and maintenance jobs SHALL not inherit these settings.

#### Scenario: Deployment uses configured Valkey
- **WHEN** the worker starts with `VALKEY_URL=valkey://valkey:6379/0`
- **THEN** Celery connects to the corresponding `redis://valkey:6379/0` endpoint
- **AND** it does not require SQLAlchemy transport tables

### Requirement: Lossless SQL-to-Valkey broker cutover
When upgrading from the SQLAlchemy transport to Valkey, workers and Beat SHALL refuse startup if the legacy SQL Kombu queue retains any messages. Deployment SHALL require stopping old Beat, draining and verifying the old worker queue, and only then switching broker transports. Non-idempotent mail tasks SHALL NOT be blindly replayed.

#### Scenario: Legacy SQL messages remain
- **GIVEN** the existing SQL broker contains queued or reserved messages
- **WHEN** new Valkey workers or Beat start
- **THEN** startup fails with remediation instructions before consuming new jobs

#### Scenario: Drained broker
- **GIVEN** the legacy SQL broker has no remaining messages
- **WHEN** new workers start with Valkey configured
- **THEN** startup proceeds and the old tables remain intact

### Requirement: Production stack runs released images behind Traefik and Keycloak
The repository SHALL provide a production Compose stack that runs the application from published release images pinned by version, terminates TLS at Traefik with automatic certificates, provides Keycloak as OIDC provider, and preserves the deployment boundaries of the development stack.

#### Scenario: Deployment pulls a released version
- **WHEN** an operator sets `APP_VERSION` to a released version and starts the production stack
- **THEN** backend, worker, beat, migrate and frontend run the GHCR images of that version, nothing is built on the server, and Compose refuses to start without `APP_VERSION`

#### Scenario: Only the TLS proxy is public
- **WHEN** the production stack is running
- **THEN** only Traefik publishes ports (80 redirecting to 443), no container mounts the Docker socket, and databases and cache are attached only to internal networks

#### Scenario: Keycloak administration is restricted
- **WHEN** a client outside `KEYCLOAK_ADMIN_ALLOWED_IPS` requests `/admin` or the `master` realm on the auth host
- **THEN** Traefik answers 403, while the application realm stays publicly reachable

#### Scenario: Secrets stay with their consumers
- **WHEN** the production stack starts
- **THEN** the application database owner password reaches only `db` and `migrate`, the Keycloak admin and database credentials reach only `keycloak` and `keycloak-db`, and runtime services still wait for the one-shot migration

#### Scenario: Forwarded headers are trusted only from the proxy hop
- **WHEN** a client sends its own `X-Forwarded-For` header
- **THEN** neither the audit log nor rate limiting use it, and Keycloak derives scheme and host only from headers sent by the proxy network

#### Scenario: Admin allowlist is closed by default
- **WHEN** `KEYCLOAK_ADMIN_ALLOWED_IPS` is not set
- **THEN** the Keycloak administration is reachable only from the server itself (`127.0.0.1/32`)

#### Scenario: Existing Traefik on the host
- **WHEN** the operator adds `deploy/compose/existing-traefik.yml`
- **THEN** the bundled Traefik does not start, frontend and Keycloak join the operator's external proxy network and publish their routes, the admin allowlist and HSTS through labels, and still no container of the stack publishes ports or mounts the Docker socket

#### Scenario: Existing Keycloak on the host
- **WHEN** the operator adds `deploy/compose/existing-keycloak.yml`
- **THEN** the bundled Keycloak and its database do not start, the bundled Traefik serves no Keycloak routes, and the auth host is no longer aliased to Traefik inside the stack
