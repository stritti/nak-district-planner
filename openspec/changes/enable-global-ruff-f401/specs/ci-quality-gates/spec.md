## ADDED Requirements

### Requirement: Backend unused imports SHALL be rejected globally
The standard backend CI SHALL run pinned Ruff `uv run ruff check .` with F401 enabled for production modules, Alembic migrations, utilities and tests. F401 SHALL NOT be globally ignored, and the obsolete isolated partial-scope step SHALL be removed.

#### Scenario: Unused import introduced anywhere in backend
- **WHEN** a production module, migration or test introduces an import not referenced or intentionally exported
- **THEN** the global Ruff CI step fails with F401

#### Scenario: All imports valid
- **WHEN** all imports are used or explicitly exported
- **THEN** the pinned full-backend Ruff check passes without special directory allowlists

### Requirement: Registration and compatibility imports SHALL be preserved
The ORM registry SHALL import its 32 known mapped classes and declare public exports so Alembic registers them with `Base.metadata`. Compatibility imports used as documented patch targets SHALL remain available.

#### Scenario: ORM metadata registration
- **WHEN** the ORM registry loads
- **THEN** every declared model export exists and its mapped table belongs to `Base.metadata`

#### Scenario: A compatibility patch target is used by an integration test
- **WHEN** a test patches the calendar router's `encrypt_credentials` symbol
- **THEN** the symbol remains importable even though the router does not call it directly

#### Scenario: Invalid unused-import fixture
- **WHEN** Ruff runs on a fixture containing an unused `uuid` import with project config
- **THEN** it returns an F401 failure; a fixture that uses the import passes
