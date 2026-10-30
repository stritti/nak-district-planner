## Implementation
- [x] Inspect new domain scope and identify unused imports.
- [x] Expand isolated Ruff F401 CI gate without hiding the global ignore.
- [x] Remove the two F401 imports flagged by CI run 40028745839 (NotificationType, EventApprovalStatus) after observing the failing gate.
- [x] Run CI Ruff, unit tests, PostgreSQL RLS integration, docs and OpenSpec checks.
- [x] Request Codex review and update issue #715 with measured progress.

> Superseded by `enable-global-ruff-f401` (PR #741, issue #715 closed): F401 now applies to the whole backend, so this partial-scope requirement was archived without merging it into the baseline.
