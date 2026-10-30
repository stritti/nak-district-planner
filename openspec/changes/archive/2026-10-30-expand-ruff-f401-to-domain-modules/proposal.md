## Why
Issue #715 established Ruff F401 on two registration production modules in merged PR #719. The backend still ignores unused imports globally. The domain ports, conflict rules and mapping services form the next coherent, reviewable boundary.

## What Changes
- Extend the isolated F401 CI gate to the complete `app/domain/ports`, `app/domain/planning` and `app/domain/services` directories in addition to both existing files.
- Remove diagnosed unused imports from the domain repository ports while preserving their public interfaces and runtime behavior.
- Keep the project-wide F401 ignore until all legacy modules have been audited.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: expand the non-bypassable F401 scope.

## Impact
GitHub workflow, one domain-port imports file, docs and OpenSpec. No API or DB changes.
