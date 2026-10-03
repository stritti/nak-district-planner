## ADDED Requirements

### Requirement: Dependency caches are deterministic accelerators
The CI pipeline SHALL use dependency caches only as optional accelerators and SHALL keep lockfiles authoritative for dependency installation.

#### Scenario: Backend cache hit
- **WHEN** a backend workflow runs with an unchanged `uv.lock`
- **THEN** the `uv` cache SHALL be restored and `uv sync --frozen` SHALL install exactly the locked dependency set

#### Scenario: Backend cache miss
- **WHEN** no matching `uv` cache exists
- **THEN** the workflow SHALL still complete dependency installation from the lockfile without changing it

#### Scenario: Frontend partial cache hit
- **WHEN** the exact Bun cache key is unavailable but a cache for the same runner OS and Bun version exists
- **THEN** the workflow SHALL restore reusable package data and `bun install --frozen-lockfile --prefer-offline` SHALL fetch any missing packages normally

### Requirement: Playwright browser downloads are reusable
The E2E workflow SHALL cache the Chromium browser by runner OS and frontend lockfile state.

#### Scenario: Browser cache hit
- **WHEN** the Playwright browser cache key matches
- **THEN** the workflow SHALL skip the Chromium download and execute the same E2E test suite

#### Scenario: Browser dependency changes
- **WHEN** `services/frontend/bun.lock` changes
- **THEN** the browser cache key SHALL change and Chromium SHALL be installed before E2E tests run

### Requirement: Security scans avoid unnecessary installation work
Security workflows SHALL preserve CodeQL and dependency-audit coverage while omitting setup steps that are not required by the scanner.

#### Scenario: Frontend dependency audit
- **WHEN** `bun audit` runs with a valid `bun.lock`
- **THEN** the workflow SHALL audit the lockfile without installing `node_modules` first

#### Scenario: Interpreted-language CodeQL scan
- **WHEN** CodeQL analyzes Python or JavaScript/TypeScript
- **THEN** the workflow SHALL initialize and analyze CodeQL without an unnecessary autobuild step

### Requirement: Linting preserves a fully validated branch baseline
MegaLinter SHALL validate changed files on pull requests and the complete codebase on branch pushes.

#### Scenario: Pull request validation
- **WHEN** MegaLinter runs for a pull request
- **THEN** only new or edited files SHALL be selected for linting against the default branch

#### Scenario: Branch baseline validation
- **WHEN** MegaLinter runs for a push to `main` or `develop`
- **THEN** the complete codebase SHALL be validated

### Requirement: Existing quality gates remain unchanged
Pipeline performance changes SHALL NOT reduce the existing test, migration, coverage, or security requirements.

#### Scenario: Backend coverage
- **WHEN** backend unit tests finish
- **THEN** CI SHALL still fail if total application coverage is below 80 percent

#### Scenario: Database regression checks
- **WHEN** backend integration and performance tests run
- **THEN** skipped tests SHALL still fail the CI job and Alembic SHALL still perform its migration graph, roundtrip, seed and schema-drift checks

#### Scenario: Cache infrastructure unavailable
- **WHEN** a dependency or browser cache cannot be restored
- **THEN** the workflow SHALL fall back to normal installation and SHALL execute the same quality gates
