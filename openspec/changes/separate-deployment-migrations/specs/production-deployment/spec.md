## MODIFIED Requirements

### Requirement: Database migrations run before runtime services
Schema-changing migrations SHALL execute as a dedicated one-shot deployment step with migration credentials. API and worker processes SHALL NOT execute Alembic upgrades during application startup.

#### Scenario: Normal stack startup
- **WHEN** the Compose stack is started
- **THEN** the migration service waits for a healthy database
- **AND** applies `alembic upgrade head`
- **AND** backend and worker start only after migration completion succeeds

#### Scenario: Migration fails
- **WHEN** the migration service exits unsuccessfully
- **THEN** backend and worker do not start

### Requirement: Runtime credentials cannot perform deployment DDL
Backend and worker SHALL load only runtime database credentials. Migration-owner credentials SHALL be scoped to the migration service.
