## Why
Issue #715 tracks elimination of the global Ruff F401 suppression. Merged PRs #719 and #720 protect registration code and domain ports/planning/services. Python domain models still contain unused `enum.Enum` imports that are hidden by the global ignore.

## What Changes
- Require the existing isolated F401 CI gate to cover all Python files in `app/domain/models`, including any new modules.
- Remove the five genuinely unused `Enum` imports identified by CI.
- Preserve the explicit `__all__` reexports in `models/__init__.py` and existing `StrEnum` runtime types.
- Record the red/green verification and keep the global ignore until other backend directories are audited.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: cover the complete domain model package.

## Impact
GitHub Actions backend CI, five import-only edits, documentation and OpenSpec. No API, DB, or model behavior changes.
