## ADDED Requirements

### Requirement: Ponytail is available to every configured AI coding agent
The repository SHALL expose the complete Ponytail skill suite to every AI coding agent that already has a repo-local skill directory.

#### Scenario: Agent discovers coding skills
- **WHEN** Claude, Codex, Gemini, GitHub Copilot, OpenCode, Qwen, or the generic agent host loads repository skills
- **THEN** `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, and `ponytail-help` SHALL be available

### Requirement: Mirrored Ponytail skills remain identical across agent hosts
All agent-specific copies SHALL reference identical Git blob contents for each Ponytail skill and SHALL be sourced from one pinned upstream release.

#### Scenario: Ponytail integration is reviewed
- **WHEN** the repository tree is compared across the seven skill hosts
- **THEN** each Ponytail skill SHALL have identical content in every host
- **AND** the OpenSpec proposal SHALL record the upstream commit used

### Requirement: Third-party license is preserved
The repository SHALL retain the Ponytail MIT license alongside the mirrored integration.

#### Scenario: License compliance is inspected
- **WHEN** a contributor reviews the vendored Ponytail skills
- **THEN** the upstream copyright and MIT permission notice SHALL be available in the repository
