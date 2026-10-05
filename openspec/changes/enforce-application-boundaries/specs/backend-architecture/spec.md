## MODIFIED Requirements

### Requirement: Application dependencies point inward
Application modules SHALL depend on domain models, domain services, and domain ports instead of concrete adapters or persistence frameworks.

#### Scenario: New application module imports an adapter
- **WHEN** a new or previously clean module below `app/application` imports `app.adapters.*`
- **THEN** the architecture test fails
- **AND** the dependency must be moved behind a domain port/interface

#### Scenario: New application module imports SQLAlchemy directly
- **WHEN** a new or previously clean module below `app/application` imports `sqlalchemy*`
- **THEN** the architecture test fails
- **AND** persistence concerns must be moved behind a domain port or adapter boundary

#### Scenario: Existing legacy dependency remains
- **WHEN** an RC-1 legacy module still imports an adapter or SQLAlchemy
- **THEN** it is accepted only when that file is explicitly present in the documented Legacy-Allowlist
- **AND** no new file may be added to the allowlist as part of normal feature development

#### Scenario: Legacy dependency is removed
- **WHEN** an allowlisted application module no longer imports the corresponding infrastructure namespace
- **THEN** the architecture test fails as stale
- **AND** the obsolete allowlist entry must be deleted

### Requirement: Runtime version metadata uses one source of truth
FastAPI/OpenAPI metadata, health information, and version APIs SHALL derive the running application version from the centrally resolved package version.

#### Scenario: Application metadata is created
- **WHEN** the FastAPI application is initialized
- **THEN** its `version` is `settings.app_version`
- **AND** no unrelated hardcoded API version is used

### Requirement: RC documentation reflects deployed security and operations
Release-facing architecture, security, and production runbook documentation SHALL describe the mechanisms and required checks that are actually active for the RC.

#### Scenario: Completed OpenSpec change no longer represents active work
- **WHEN** every implementation task of a change is completed and the behavior is part of the release baseline
- **THEN** the change is moved to the OpenSpec archive
- **AND** its historical proposal, design, tasks, and delta specs remain available
