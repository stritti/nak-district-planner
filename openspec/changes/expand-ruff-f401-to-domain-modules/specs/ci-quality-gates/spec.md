## ADDED Requirements

### Requirement: Ruff F401 SHALL cover all reviewed domain components
The backend CI SHALL run an isolated Ruff F401 check for both registration modules already covered by #719 and **every module** in the `app/domain/ports`, `app/domain/planning`, and `app/domain/services` directories, independently of the global F401 ignore. This applies to newly introduced files in those directories without needing an allow-list update.

#### Scenario: Reviewed modules have no unused imports
- **WHEN** CI runs against the selected module files and full domain directories
- **THEN** the Ruff F401 check succeeds

#### Scenario: An unused import is introduced in any reviewed domain directory
- **WHEN** a developer introduces an unused import in a newly added or existing module under the selected directories
- **THEN** CI fails even though F401 remains in the project-wide ignore list

#### Scenario: Existing registration gate stays effective
- **WHEN** an unused import is introduced in either registration module from PR #719
- **THEN** the expanded F401 gate fails as before
