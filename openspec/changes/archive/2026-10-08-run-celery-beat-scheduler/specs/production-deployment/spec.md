## ADDED Requirements

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
