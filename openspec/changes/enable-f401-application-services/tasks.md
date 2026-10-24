## Implementation
- [x] Add the application directory to the isolated F401 CI gate, preserving the original paths.
- [x] Observe RED failure and retain exact diagnostics from GitHub Actions run 40086639329.
- [x] Remove the five diagnosed unused imports without changing runtime behavior.
- [ ] Verify GREEN F401 and all backend Python unit, PostgreSQL RLS and frontend tests on current head; coverage >80%.
- [ ] Validate OpenSpec, security, migration and request independent Codex code review.
- [ ] Update issue #715, keeping it open for adapters/test modules and final global F401 removal.
