# ci-quality-gates Specification

## Purpose

Defines the GitHub Actions quality gates that protect `main`: tests and coverage, migration checks, security scans, linting, documentation and OpenSpec validation, with caches used only as accelerators.

## Requirements

### Requirement: Backend and frontend test gates
CI SHALL install backend dependencies with `uv sync --locked`, run Ruff and the RBAC guard check, run PostgreSQL integration tests with RLS against a freshly migrated database, and fail when total backend unit-test coverage is below 80 percent. Frontend CI SHALL install with `bun install --frozen-lockfile`, run ESLint, unit tests and Playwright E2E tests.

#### Scenario: Coverage drops
- **WHEN** backend coverage falls below 80 percent
- **THEN** the CI job fails

### Requirement: Migration check
The Alembic workflow SHALL verify a single head, FK name lengths, offline SQL, upgrade to head, a downgrade/upgrade roundtrip, a seed dry-run and `alembic check` schema drift.

#### Scenario: Model drift
- **WHEN** ORM models differ from the migrated schema
- **THEN** `alembic check` fails the workflow

### Requirement: Security and lint gates
Security scans SHALL run CodeQL, `pip-audit` on the exported lock and `bun audit --audit-level=moderate` without `continue-on-error`; dependency review SHALL run on pull requests. MegaLinter (Python flavor) SHALL lint changed files on pull requests against the actual base branch and the full codebase on pushes.

#### Scenario: Vulnerable frontend dependency
- **WHEN** `bun audit` reports a moderate or higher advisory
- **THEN** the security workflow fails

### Requirement: Documentation and OpenSpec gate
The `docs` workflow SHALL run on every pull request to `main`, validate all OpenSpec changes and specs with a pinned OpenSpec CLI, and build the VitePress site from the root lockfile.

#### Scenario: Invalid spec delta
- **WHEN** a pull request adds a requirement without a scenario
- **THEN** the `Build documentation` check fails

### Requirement: Caches are accelerators only
Dependency and Playwright caches SHALL NOT change which lockfile versions are installed or which gates run; a cache miss SHALL fall back to normal installation.

#### Scenario: Cache miss
- **WHEN** no cache entry matches
- **THEN** the workflow installs from the lockfile and runs the same gates
