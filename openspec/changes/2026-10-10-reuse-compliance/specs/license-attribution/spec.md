# License attribution

## ADDED Requirements

### Requirement: REUSE verification across the repository
The project SHALL be auditable by REUSE 3.3, with a valid SPDX license file for every declared license and copyright/license attribution for every tracked file.

#### Scenario: Non-commentable files
- **WHEN** a binary asset or lockfile cannot hold an inline SPDX comment
- **THEN** REUSE metadata SHALL associate the AGPL project notice without modifying that file.

#### Scenario: Third-party MIT agent skills
- **WHEN** mirrored OpenSpec/Ponytail skills are checked
- **THEN** metadata SHALL associate MIT and the upstream attribution instead of treating these resources as newly AGPL-owned.

#### Scenario: Missing license text
- **WHEN** code metadata references a missing SPDX license text
- **THEN** the REUSE CI gate SHALL fail.

### Requirement: Keep strict SPDX source checks
REUSE validation SHALL supplement and not replace source-language-specific SPDX validation or executable-mode checks.

#### Scenario: A source file uses an invalid comment
- **WHEN** the file passes fallback license association but has an invalid source-level SPDX header
- **THEN** the existing strict check SHALL reject it.
