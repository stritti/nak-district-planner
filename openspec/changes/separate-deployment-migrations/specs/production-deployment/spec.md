## ADDED Requirements

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
