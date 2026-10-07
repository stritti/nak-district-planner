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
