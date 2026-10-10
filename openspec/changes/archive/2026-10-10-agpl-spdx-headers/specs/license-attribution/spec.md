# License attribution specification

## Purpose
Identify the license and copyright owner for every maintained source file, while preserving third-party legal notices.

## Requirements

### Requirement: SPDX identity for first-party code
Every tracked first-party source under services/backend/, services/frontend/, idp-deploy/, scripts/ and docs/.vitepress/, plus the root compatibility shell script, MUST carry the lines "SPDX-FileCopyrightText: 2026 Stephan Strittmatter" and "SPDX-License-Identifier: AGPL-3.0-only" in a language-appropriate leading comment.

#### Scenario: New source file without metadata
- **WHEN** a new maintained Python, TypeScript, Vue, JavaScript, HTML, CSS, shell or Alembic template source file lacks attribution
- **THEN** the license CI check fails with its path.

#### Scenario: Non-AGPL or conflicting metadata
- **WHEN** the metadata is incomplete or gives a different license
- **THEN** automated checks fail rather than silently relicensing the file.

### Requirement: Preserve syntax and program behavior
License annotation MUST preserve source semantics, including shebangs, Python encoding declarations, HTML doctypes and Vue SFC parsing.

#### Scenario: Executable shell file
- **WHEN** a tracked executable shell script is annotated
- **THEN** its shebang stays on the first line and the added lines are shell comments.

#### Scenario: Vue single-file component
- **WHEN** a Vue component is annotated
- **THEN** HTML comments precede template/script/style blocks and remain parseable.

### Requirement: Honor third-party licensing
Vendored dependencies, external agent skills, binaries, generated artifacts and upstream license texts MUST NOT be relicensed by automation.

#### Scenario: Imported third-party material
- **WHEN** the repository contains Ponytail or another upstream dependency
- **THEN** the upstream copyright/license notices are preserved and excluded from the first-party scanner.
