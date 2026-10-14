## Why

RC-1 contains application-layer modules that still instantiate or import concrete adapters. A broad refactor directly before RC-2 would create unnecessary release risk, but leaving the dependency direction unenforced would allow the debt to grow unnoticed.

Release metadata and operational documentation also contain RC-1 inconsistencies that should be removed before the next release candidate.

## What Changes

- Freeze the existing `app.application -> app.adapters` debt in an explicit, tested legacy allowlist.
- Reject adapter dependencies from new application modules so new use cases must depend on domain ports/interfaces.
- Report the FastAPI application version from the same package metadata used by health and system endpoints.
- Align architecture, security, operations, and release documentation with the RC-2 trust and deployment boundaries.
- Archive the completed `approved-idp-login-scoped-access` change; the remaining finished changes are archived in a separate OpenSpec sync PR.

## Capabilities

### Added Capabilities

- `architecture-governance`: automated dependency-direction checks prevent new application-to-adapter coupling while explicitly tracking legacy debt.

### Modified Capabilities

- `operational-readiness`: runtime version and RC-2 operational documentation use the current deployment and bootstrap model.

## Impact

- No runtime feature behavior changes except that FastAPI metadata reports the real package version.
- Existing legacy dependency violations remain functional but cannot silently spread to new application modules.
- Follow-up refactors can shrink the allowlist incrementally after RC-2.
