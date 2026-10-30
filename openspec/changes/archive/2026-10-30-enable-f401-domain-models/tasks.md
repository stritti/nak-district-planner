## Implementation
- [x] Record scope and extend the existing isolated F401 gate to `app/domain/models`.
- [x] Observe RED in GitHub Actions: run 40030528685 reported exactly five unused `Enum` imports.
- [x] Remove only those five identified unused imports, keeping all `StrEnum` types.
- [x] Verify GREEN on the new PR head and full backend unit/PostgreSQL RLS, coverage >80% and frontend CI.
- [x] Validate OpenSpec/docs/security and obtain an independent Codex review.
- [x] Update #715 and document remaining migration scope.

> Superseded by `enable-global-ruff-f401` (PR #741, issue #715 closed): F401 now applies to the whole backend, so this partial-scope requirement was archived without merging it into the baseline.
