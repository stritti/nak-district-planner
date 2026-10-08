## ADDED Requirements

### Requirement: Workflow actions are pinned to immutable commits
Every action referenced by a GitHub Actions workflow SHALL be pinned to a full 40-character commit SHA. The human-readable release version SHALL be recorded as a trailing comment so that automated dependency updates can bump SHA and version together.

#### Scenario: Upstream tag is moved
- **WHEN** the maintainer of a referenced action re-points a release tag to a different commit
- **THEN** the workflows keep executing the previously reviewed commit
- **AND** the change only takes effect through a reviewable dependency-update pull request

### Requirement: Workflow token permissions follow least privilege
Workflows SHALL grant `contents: read` by default. Write scopes SHALL be granted only to the jobs that need them.

#### Scenario: CI test jobs run on a pull request
- **WHEN** the frontend or E2E jobs of the CI workflow run
- **THEN** their token cannot write pull-request comments
- **AND** only the backend coverage job receives `pull-requests: write`
