## Why
The backend's global `F401` ignore hides unused imports in all Python modules. Enabling the rule without first triaging intentional reexports could break the release and distract from higher-priority security work. This is the first independently enforceable, low-risk step of #715.

## What Changes
- Remove one confirmed unused `Enum` import in the registration domain.
- Run a dedicated Ruff `--isolated --select F401` check on the registration domain model and API router on every backend CI execution.
- Preserve existing global ignore elsewhere until import/reexport usage has been triaged.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: incremental unused-import enforcement.

## Impact
CI workflow, one Python import, documentation/OpenSpec. No runtime behavior change.
