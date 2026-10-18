## ADDED Requirements

### Requirement: Dependabot auto-merge cannot bypass main-branch quality requirements

Automatic dependency merges SHALL be performed by GitHub only after all mandatory ruleset status checks succeed on an up-to-date branch. The auto-merge workflow SHALL NOT weaken test coverage thresholds, skip audits, or attempt unconditional merges.

#### Scenario: Coverage regression in an otherwise valid minor update
- **WHEN** a minor update fails a required frontend or backend coverage check
- **THEN** auto-merge remains blocked until the regression is corrected and checks succeed

#### Scenario: Security or E2E workflow fails
- **WHEN** a required CodeQL, dependency audit, migration, or E2E check fails
- **THEN** the patch/minor update cannot merge automatically

#### Scenario: Branch is outdated
- **WHEN** a newer commit is merged into `main` and strict up-to-date checks are required
- **THEN** an eligible Dependabot PR waits for a fresh validation against the current base
