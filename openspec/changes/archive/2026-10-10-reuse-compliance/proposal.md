# Make the repository REUSE-compliant

## Why

The repository already has AGPLv3 SPDX headers in first-party source files, but unannotated documentation, configuration, lockfiles, assets and imported agent skills are not covered by a standard whole-tree audit.

## What changes

- Add REUSE 3.3 metadata with AGPL fallback and MIT exceptions for imported agent skills.
- Add matching license texts for AGPL-3.0-only and MIT.
- Enforce `reuse lint` on pull requests and main while retaining strict custom source and executable mode checks.
- Document attribution and verify metadata with focused unit tests.

## Non-goals

No changes to application behavior, ownership, license version or imported original notices.
