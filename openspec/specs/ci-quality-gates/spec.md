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
The `docs` workflow SHALL run on every pull request to `main`, strictly validate all baseline specifications and active changes with a pinned OpenSpec CLI using `validate --all --strict --no-interactive`, and build the VitePress site from the root lockfile.

#### Scenario: Invalid spec delta
- **WHEN** a pull request adds an invalid baseline requirement or active change without a complete scenario
- **THEN** the `Build documentation` check fails

#### Scenario: Invalid active spec delta
- **WHEN** a pull request contains an invalid active OpenSpec change
- **THEN** the existing required `Build documentation` status fails

#### Scenario: Valid baseline and active changes
- **WHEN** all baseline specifications and active changes validate strictly
- **THEN** the documentation build continues with frozen dependencies

### Requirement: Caches are accelerators only
Dependency and Playwright caches SHALL NOT change which lockfile versions are installed or which gates run; a cache miss SHALL fall back to normal installation.

#### Scenario: Cache miss
- **WHEN** no cache entry matches
- **THEN** the workflow installs from the lockfile and runs the same gates

### Requirement: Backend unused imports SHALL be rejected globally
The standard backend CI SHALL run pinned Ruff `uv run ruff check .` with F401 enabled for production modules, Alembic migrations, utilities and tests. F401 SHALL NOT be globally ignored, and the obsolete isolated partial-scope step SHALL be removed.

#### Scenario: Unused import introduced anywhere in backend
- **WHEN** a production module, migration or test introduces an import not referenced or intentionally exported
- **THEN** the global Ruff CI step fails with F401

#### Scenario: All imports valid
- **WHEN** all imports are used or explicitly exported
- **THEN** the pinned full-backend Ruff check passes without special directory allowlists

### Requirement: ORM registration and compatibility symbols SHALL be preserved
The ORM registry SHALL import its 32 known mapped classes and declare public exports so Alembic registers them with `Base.metadata`. Compatibility symbols used as documented patch targets SHALL remain available without unused-import suppressions.

#### Scenario: ORM metadata registration
- **WHEN** the ORM registry loads
- **THEN** every declared model export exists and its mapped table belongs to `Base.metadata`

#### Scenario: A compatibility patch target is used by an integration test
- **WHEN** a test patches the calendar router's `encrypt_credentials` symbol
- **THEN** the symbol remains importable even though the router does not call it directly

#### Scenario: Invalid unused-import fixture
- **WHEN** Ruff runs on a fixture containing an unused `uuid` import with project config
- **THEN** it returns an F401 failure; a fixture that uses the import passes

### Requirement: Patched frontend dependency versions SHALL be installed and audited
The frontend's frozen Bun lockfile SHALL resolve direct `happy-dom` to version 21.0.4 or newer and transitive `fast-uri` to patched 3.1.9 or newer within the compatible major range, and CI SHALL continue to enforce `bun audit --audit-level=moderate` as a failing gate for moderate or higher advisories.

#### Scenario: Patched dependency graph
- **WHEN** GitHub Actions installs the frozen Bun dependencies and audits the frontend
- **THEN** both patched package versions are installed and the audit exits successfully without exceptions

#### Scenario: Vulnerable transitive dependency reintroduced
- **WHEN** a dependency update resolves `fast-uri` to an affected version and Bun audit reports a moderate advisory
- **THEN** the existing Security Scans workflow fails instead of suppressing the finding

#### Scenario: Vulnerable test DOM dependency reintroduced
- **WHEN** Happy DOM resolves to an affected version and Bun audit reports its high-severity advisory
- **THEN** the existing Security Scans workflow fails

#### Scenario: Manifest and frozen lockfile diverge
- **WHEN** the Happy DOM manifest range is incompatible with its locked resolution
- **THEN** `bun install --frozen-lockfile` fails and CI blocks the change

#### Scenario: Frontend behavior after major dev dependency upgrade
- **WHEN** Vue unit tests exercise both successful interactions and expected error cases using Happy DOM 21
- **THEN** the existing behavior and coverage requirements remain satisfied
