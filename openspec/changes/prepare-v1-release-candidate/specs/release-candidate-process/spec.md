## ADDED Requirements

### Requirement: v1 stabilization uses SemVer release candidates
The release pipeline SHALL support a v1 stabilization phase using versions in the form `1.0.0-rc.N` before the stable `1.0.0` release.

#### Scenario: First v1 candidate
- **WHEN** the RC preparation change is merged with `Release-As: 1.0.0-rc.1`
- **THEN** Release Please SHALL prepare `1.0.0-rc.1` as the next release
- **AND** the GitHub release SHALL be marked as a prerelease

#### Scenario: Further stabilization release
- **WHEN** a releaserelevant bugfix is merged after `1.0.0-rc.1`
- **THEN** the prerelease versioning strategy SHALL increment the RC identifier for the next candidate

### Requirement: Release candidates do not move stable container aliases
The release workflow SHALL publish prerelease images without changing stable GHCR aliases.

#### Scenario: RC image publication
- **WHEN** `v1.0.0-rc.1` is released
- **THEN** backend and frontend images SHALL receive the exact tag `1.0.0-rc.1`
- **AND** the release SHALL NOT publish `1.0`, `1`, or `latest` for that candidate

#### Scenario: Stable image publication
- **WHEN** a stable SemVer release is published
- **THEN** the existing exact, minor, major, and `latest` image tags SHALL continue to be published

### Requirement: Release PR updates execute normal pull-request CI
Release Please SHALL use a token that allows its release-PR updates to trigger the repository's required pull-request workflows.

#### Scenario: Release token is configured
- **WHEN** the Release workflow starts with `RELEASE_PLEASE_TOKEN` configured
- **THEN** Release Please SHALL use that token directly
- **AND** SHALL NOT fall back to `GITHUB_TOKEN`

#### Scenario: Release token is missing
- **WHEN** `RELEASE_PLEASE_TOKEN` is empty or unavailable
- **THEN** the Release workflow SHALL fail before invoking Release Please
- **AND** SHALL report that the token is required for the CI-gated release PR flow

### Requirement: Documentation check is always available for branch governance
Every pull request against `main` SHALL expose a stable `Build documentation` check so the check can be required by the branch ruleset without path-filter deadlocks.

#### Scenario: Any pull request targets main
- **WHEN** a pull request targets `main`
- **THEN** `Build documentation` SHALL run `npm ci` and `npm run docs:build`
- **AND** the pull request SHALL NOT configure, upload, or deploy GitHub Pages

#### Scenario: Documentation change reaches main
- **WHEN** a documentation-relevant change is pushed to `main`
- **THEN** the documentation SHALL be built
- **AND** the existing GitHub Pages deployment SHALL run after a successful build

### Requirement: RC release requires the complete quality gate
A release candidate SHALL NOT be published unless the complete v1 quality gate has succeeded for the candidate state.

#### Scenario: Candidate checks succeed
- **WHEN** the RC release PR is ready to merge
- **THEN** Backend Unit Tests & Coverage SHALL succeed with at least 80 percent coverage
- **AND** backend integration and performance tests SHALL succeed without skips
- **AND** Frontend Unit Tests and Frontend E2E Tests SHALL succeed
- **AND** Migration Graph & FK Names SHALL succeed including the blocking schema drift check
- **AND** Encrypted Backup & Isolated Restore SHALL succeed
- **AND** MegaLinter SHALL succeed
- **AND** Dependency Review SHALL succeed
- **AND** both CodeQL analyses and both dependency audits SHALL succeed
- **AND** Docker image builds SHALL succeed
- **AND** Build documentation SHALL succeed

#### Scenario: Workflow requires manual action instead of running
- **WHEN** a required workflow on the RC release PR has conclusion `action_required` and no successful job execution
- **THEN** the RC gate SHALL be considered failed

### Requirement: Main branch governance is verified before RC publication
The RC release PR SHALL NOT be merged until the repository's `main` ruleset enforces the documented pull-request and required-status-check policy.

#### Scenario: Ruleset is incomplete
- **WHEN** the active `main` ruleset lacks the required pull-request rule or required status checks
- **THEN** the RC release PR SHALL remain unmerged
- **AND** Issue #403 SHALL remain open

#### Scenario: Ruleset is complete
- **WHEN** the active `main` ruleset matches `docs/production-runbook.md` and Issue #403
- **THEN** the governance gate SHALL be considered satisfied

### Requirement: RC phase is a feature freeze
The v1 RC phase SHALL accept stabilization changes only.

#### Scenario: Regression fix during RC
- **WHEN** a defect is fixed during the RC phase
- **THEN** targeted regression tests SHALL cover the defect and relevant exception paths
- **AND** existing coverage and quality thresholds SHALL remain unchanged

#### Scenario: New feature proposed during RC
- **WHEN** a non-essential feature is proposed after the first v1 RC
- **THEN** it SHALL NOT be included in the v1.0 stabilization line

### Requirement: Stable v1 promotion is explicit
Promotion from the final RC to `v1.0.0` SHALL be a separate reviewed release step.

#### Scenario: Promote final candidate
- **WHEN** the final candidate has passed the complete v1 gate
- **THEN** a separate change SHALL disable Release Please prerelease mode
- **AND** its merge SHALL request `Release-As: 1.0.0`
- **AND** the resulting stable release SHALL again publish the stable GHCR aliases
