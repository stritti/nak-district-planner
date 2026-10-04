## 1. Architecture boundary

- [x] 1.1 Add an AST-based regression test for `app.application -> app.adapters` dependencies.
- [x] 1.2 Record the RC-2 legacy adapter-import files with explicit rationales.
- [x] 1.3 Verify the architecture test against the full backend unit suite.

## 2. Release metadata

- [x] 2.1 Use `settings.app_version` for FastAPI metadata.
- [x] 2.2 Add a regression test for the single version source of truth.

## 3. Documentation and OpenSpec

- [x] 3.1 Update the production runbook for the current owner-controlled superadmin bootstrap.
- [x] 3.2 Update the runbook/release documentation for the current required CI checks.
- [x] 3.3 Align architecture/security status documents with the RC-2 dependency and trust boundaries.
- [x] 3.4 Archive completed OpenSpec changes and consolidate their implemented capability specs into the baseline.

## 4. Verification

- [x] 4.1 Backend tests pass with coverage >80%.
- [x] 4.2 Architecture regression tests pass for both allowed legacy debt and rejected new dependencies.
- [x] 4.3 MegaLinter/OpenSpec checks pass.
