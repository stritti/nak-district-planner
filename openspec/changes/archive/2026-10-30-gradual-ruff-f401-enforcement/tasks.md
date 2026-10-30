## Implementation
- [x] Remove confirmed unused Enum import from registration model.
- [x] Add isolated Ruff F401 gate for two registration modules.
- [x] Record scoped enforcement in OpenSpec.
- [x] Verify backend CI and continue incremental expansion under #715.

> Superseded by `enable-global-ruff-f401` (PR #741, issue #715 closed): F401 now applies to the whole backend, so this partial-scope requirement was archived without merging it into the baseline.
