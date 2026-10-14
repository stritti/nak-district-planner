## 1. Architecture boundary

- [x] 1.1 Add an AST-based regression test for `app.application -> app.adapters` dependencies.
- [x] 1.2 Record the RC-2 legacy adapter imports per file (exact imported modules) with explicit rationales; reject stale entries.
- [x] 1.3 Verify the architecture test against the full backend unit suite.
- [x] 1.4 Resolve relative imports and `from app import adapters` in the scanner; negative tests for each spelling.
- [x] 1.5 Enforce a framework-free `app.domain` (no allowlist); verified by planting a violation in each layer.

## 2. Release metadata

- [x] 2.1 Use `settings.app_version` for FastAPI metadata.
- [x] 2.2 Add a regression test for the single version source of truth.

## 3. Documentation and OpenSpec

- [x] 3.1 Update the production runbook for the current owner-controlled superadmin bootstrap.
- [x] 3.2 Update the runbook/release documentation for the current required CI checks.
- [x] 3.3 Align architecture/security status documents with the RC-2 dependency and trust boundaries.
- [x] 3.4 Archive the completed `approved-idp-login-scoped-access` change; archiving the remaining finished changes is deferred to a separate OpenSpec sync PR.

## 4. Verification

- [x] 4.1 Backend tests pass with coverage >80%.
- [x] 4.2 Architecture regression tests pass for both allowed legacy debt and rejected new dependencies.
- [x] 4.3 MegaLinter/OpenSpec checks pass.
