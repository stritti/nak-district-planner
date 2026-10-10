# License attribution requirements

## MODIFIED Requirements

### Requirement: Attribution comments must be syntactically valid
The system SHALL accept SPDX attribution only in the exact leading source-language comment format, preserving leading shebangs, doctype, Python encoding cookies and CSS charset directives.

#### Scenario: Wrong HTML comment
- **WHEN** an HTML file contains Python-style SPDX comment lines
- **THEN** the CI checker SHALL reject them.

#### Scenario: Python encoding or CSS charset directive
- **WHEN** a Python source begins with `coding:` or `coding=`, or CSS begins with `@charset`
- **THEN** generated attribution SHALL follow the declaration without invalidating it.

### Requirement: Existing licenses must not be replaced
The automatic annotation tool SHALL refuse to modify sources containing third-party copyright or license notices, including conventional `Licensed under ...` comments and docstrings.

#### Scenario: Apache-licensed header
- **WHEN** a file declares `Licensed under the Apache License, Version 2.0`
- **THEN** `--fix` SHALL refuse the operation and require manual review.

### Requirement: Preserve executable source modes
The project SHALL preserve the Git executable mode of its tracked executable scripts and fail CI when one loses mode `100755`.

#### Scenario: Backup script mode regression
- **WHEN** `scripts/backup.sh` is tracked with `100644`
- **THEN** the SPDX checker SHALL report an error.
