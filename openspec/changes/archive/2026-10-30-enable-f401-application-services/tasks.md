## Implementation
- [x] Add the application directory to the isolated F401 CI gate, preserving the original paths.
- [x] Observe RED failure and retain exact diagnostics from GitHub Actions run 40086639329.
- [x] Remove the five diagnosed unused imports without changing runtime behavior.
- [x] Verify GREEN F401 and all backend Python unit, PostgreSQL RLS and frontend tests on current head; coverage >80%.
- [x] Validate OpenSpec, security, migration and request independent Codex code review.
- [x] Update issue #715, keeping it open for adapters/test modules and final global F401 removal.

> Superseded by `enable-global-ruff-f401` (PR #741, issue #715 closed): F401 now applies to the whole backend, so this partial-scope requirement was archived without merging it into the baseline.
