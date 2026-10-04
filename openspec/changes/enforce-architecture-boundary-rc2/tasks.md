## 1. Architecture boundary

- [x] 1.1 Add an AST-based regression test for `app.application -> app.adapters` dependencies.
- [x] 1.2 Record the RC-2 legacy adapter-import files with explicit rationales.
- [ ] 1.3 Verify the architecture test against the full backend unit suite.

## 2. Release metadata

- [ ] 2.1 Use `settings.app_version` for FastAPI metadata.
- [ ] 2.2 Add a regression test for the single version source of truth.

## 3. Documentation and OpenSpec

- [ ] 3.1 Update the production runbook for the current owner-controlled superadmin bootstrap.
- [ ] 3.2 Update the runbook/release documentation for the current required CI checks.
- [ ] 3.3 Align architecture/security status documents with the RC-2 dependency and trust boundaries.
- [ ] 3.4 Archive completed OpenSpec changes whose behavior is represented by the baseline specs.

## 4. Verification

- [ ] 4.1 Backend tests pass with coverage >80%.
- [ ] 4.2 Architecture regression tests pass for both allowed legacy debt and rejected new dependencies.
- [ ] 4.3 MegaLinter/OpenSpec checks pass.
