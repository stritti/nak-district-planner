## Work items
- [x] Identify vulnerable locked packages and upstream patched versions.
- [x] Update frontend direct Happy DOM spec and both locked versions with correct SHA512 integrity values.
- [x] Verify `bun install --frozen-lockfile` succeeds on both frontend and root documentation jobs.
- [x] Verify `bun audit --audit-level=moderate` returns 0 without an ignore.
- [x] Confirm Frontend Vitest coverage, negative-path tests, lint, Vite/PWA build and Playwright E2E.
- [x] Confirm OpenSpec, backend tests, PostgreSQL RLS and >80% backend coverage.
- [x] Obtain Codex review and link the validated PR to issue #723.
- [x] Close #723 only after the fix is merged and main CI passes.
