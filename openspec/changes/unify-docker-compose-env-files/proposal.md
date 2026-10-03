# Centralize Docker Compose container environment overrides

## Why

Docker-specific runtime values are currently split between `.env`, `docker-compose.yml`, and `docker-compose.override.yml`. Backend and worker duplicate the same internal database and Valkey URLs, while the migration and test database services keep additional overrides inline. This makes it easy for development and production Compose definitions to drift.

## What Changes

- Add a shared `.env.docker` file for Docker-internal backend/worker overrides.
- Add narrowly scoped `.env.docker.migrate` and `.env.docker.test` files for the privileged migration URL and test database name.
- Load the env files through `env_file` in `docker-compose.yml` and remove active inline `environment` blocks from the application Compose definitions.
- Keep `.env` as the user-managed source for secrets and host-local values; Docker-specific files derive values from it through Compose interpolation.
- Update `.env.example` comments to document the split between host-local and container-internal URLs.
- Add regression tests for env-file wiring, required-variable handling, test isolation, and migration credential isolation.

## Impact

Docker Compose configuration gains a single explicit place for shared container networking overrides while preserving host-local `.env` behavior. No application runtime code changes, so the existing backend coverage threshold remains unchanged; the new configuration regression tests run with the backend unit test suite.
