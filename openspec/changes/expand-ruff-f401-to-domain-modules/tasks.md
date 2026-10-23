## Implementation
- [x] Inspect new domain scope and identify unused imports.
- [x] Expand isolated Ruff F401 CI gate without hiding the global ignore.
- [x] Remove the two F401 imports flagged by CI run 40028745839 (NotificationType, EventApprovalStatus) after observing the failing gate.
- [ ] Run CI Ruff, unit tests, PostgreSQL RLS integration, docs and OpenSpec checks.
- [ ] Request Codex review and update issue #715 with measured progress.
