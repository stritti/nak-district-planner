## Implementation
- [x] Add `app/adapters/api/schemas` (17 modules) to the existing CI Ruff F401 gate.
- [x] Verify that the extended gate identifies no unused schema imports (CI 40098618093, isolated F401 step green).
- [x] Preserve existing domain, application, registration and adapter checks.
- [ ] Complete combined backend unit/exception/PG-RLS tests and >80% coverage, frontend and security checks on latest PR head.
- [ ] Request Codex review; record verified results and update #715.
- [ ] Keep issue #715 open for routers, database adapters, tests and final removal of global F401 ignore.
