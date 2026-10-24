## Implementation
- [x] Identify a cohesive six-directory adapter group (33 Python modules).
- [x] Add those directories to Ruff's isolated F401 CI invocation while preserving previous paths.
- [x] Verify the isolated gate on the initial head: no F401 findings, so leave production imports unchanged.
- [ ] Confirm all nine relevant CI workflows and backend coverage >80% except known unrelated baseline security finding #723.
- [ ] Obtain Codex review; update issue #715 and document remaining adapter/test migration.
