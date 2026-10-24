## Implementation
- [x] Record scope and extend the existing isolated F401 gate to `app/domain/models`.
- [x] Observe RED in GitHub Actions: run 40030528685 reported exactly five unused `Enum` imports.
- [x] Remove only those five identified unused imports, keeping all `StrEnum` types.
- [ ] Verify GREEN on the new PR head and full backend unit/PostgreSQL RLS, coverage >80% and frontend CI.
- [ ] Validate OpenSpec/docs/security and obtain an independent Codex review.
- [ ] Update #715 and document remaining migration scope.
