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


### Requirement: Preserve executable file modes
The license migration MUST preserve existing Git executable mode `100755` for project shell and setup scripts, and CI MUST reject mode regression.

#### Scenario: A backup script is no longer executable
- **WHEN** a tracked executable source script loses Git mode `100755`
- **THEN** the license check reports a failure naming that file.

### Requirement: Validate correct source-language comment syntax
The validator MUST check SPDX attribution in the language-specific leading comment rather than accepting text or arbitrary comment markers.

#### Scenario: HTML source with Python-style comment markers
- **WHEN** a source file has SPDX-like strings without a valid source-language comment
- **THEN** the check fails and the auto-fixer refuses to overwrite ambiguous legal notices.

### Requirement: Reject conflicting license notices
The fixer MUST refuse automatic license additions when the file already contains other copyright or license notices, including common non-SPDX license declarations and notices in module docstrings.

#### Scenario: Existing Apache License notice
- **WHEN** a file starts with a comment stating that it is licensed under Apache License 2.0
- **THEN** no AGPL header is added and a manual review is required.

### Requirement: Keep encoding directives in place
Header addition MUST retain PEP 263 encoding cookies with either `coding:` or `coding=`, and keep a CSS `@charset` directive at the beginning of a stylesheet.

#### Scenario: Source has an encoding directive
- **WHEN** a Python or CSS source starts with a valid encoding directive
- **THEN** the generated attribution follows that directive without changing its position.

Generated VitePress output in `docs/.vitepress/dist/` and the associated cache directory MUST be excluded from source attribution checks while maintained `docs/.vitepress/*.mts` sources remain in scope.

Existing upstream copyright or license declarations in multiline HTML or CSS block comments MUST also prevent automatic relicensing.
