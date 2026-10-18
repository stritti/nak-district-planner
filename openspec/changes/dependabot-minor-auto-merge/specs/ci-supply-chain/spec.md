## ADDED Requirements

### Requirement: Verified Dependabot non-major updates can use native auto-merge

The repository SHALL only enable native auto-merge for Dependabot-authored, non-draft pull requests to `main` that the verified dependency metadata classifies as `version-update:semver-patch` or `version-update:semver-minor`. The workflow SHALL execute only base-controlled action code and SHALL NOT check out or execute pull-request content under a write-capable token.

#### Scenario: Dependabot publishes a patch update
- **WHEN** Dependabot opens an unmodified patch update against `main`
- **THEN** the workflow requests a GitHub-native squash auto-merge
- **AND** GitHub performs the merge only after all required checks and ruleset constraints pass

#### Scenario: Dependabot publishes a minor update
- **WHEN** Dependabot opens an unmodified minor update against `main`
- **THEN** the workflow requests a GitHub-native squash auto-merge
- **AND** a failed or pending required check blocks the merge

#### Scenario: Major or unclassified change
- **WHEN** Dependabot opens a major or unclassified update
- **THEN** the workflow does not request an automatic merge

#### Scenario: Untrusted changes or identity
- **WHEN** a pull request is drafted, is not authored by Dependabot, targets another branch, or contains maintainer modifications
- **THEN** it is not eligible for the automatic-merge request

#### Scenario: Repository auto-merge setting is disabled
- **WHEN** GitHub's `allow_auto_merge` setting is disabled
- **THEN** the workflow cannot schedule a native automatic merge
- **AND** the repository setting must be enabled by an administrator before this capability is operational
