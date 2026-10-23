## Implementation

- [x] Configure Release Please draft publication with forced Git-tag creation.
- [x] Add pre-build validation of draft status, tag provenance and release notes.
- [x] Build separate run-scoped image candidates and gate promotion on both digests.
- [x] Add immutable exact version tags, controlled stable alias promotion and best-effort alias rollback.
- [x] Support retry of a partial draft through explicit workflow dispatch.
- [x] Add release script failure tests and workflow contract tests.
- [x] Update release documentation and production runbook.

## Verification

- [ ] Run script regression tests and backend workflow contract tests in CI.
- [ ] Validate OpenSpec with `openspec validate --all --strict --no-interactive`.
- [ ] Verify the next real release remains Draft until all GHCR artifacts are validated.

