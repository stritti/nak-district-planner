## Decision
Enforce `F401` on two production modules that were reviewed for explicit imports, using the Ruff version already pinned in `uv.lock`. The isolated check intentionally ignores the project-wide F401 suppression. No broad suppression is added.

## Trade-off
This is phase 1. The global ignore remains until it is safe to enable F401 across all backend modules. Tracking: #715.

## Verification
The selected-path Ruff command must pass; removing or adding an unused import must fail it. Complete GitHub backend CI covers regression and >=80% coverage.
