## Implementation
- [x] Identify a cohesive six-directory adapter group (33 Python modules).
- [x] Add those directories to Ruff's isolated F401 CI invocation while preserving previous paths.
- [x] Verify the isolated gate on the initial head: no F401 findings, so leave production imports unchanged.
- [x] Confirm all nine relevant CI workflows, including Security Scans, backend coverage >80%, PostgreSQL RLS and frontend tests on the conflict-resolved merge head.
- [x] Obtain a fresh Codex review of the conflict-resolved merge head, update issue #715 and document remaining adapter/test migration.

> Superseded by `enable-global-ruff-f401` (PR #741, issue #715 closed): F401 now applies to the whole backend, so this partial-scope requirement was archived without merging it into the baseline.
