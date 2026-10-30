## Why
Issue #715 removes the project-wide Ruff F401 suppression incrementally. Registration, domain ports/planning/services and domain models are already protected by merged changes #719–#721. Integration adapter code remains exempt by the global ignore.

## What Changes
- Extend the existing isolated F401 gate to all 33 Python modules in six coherent adapter directories: `auth`, `idp`, `mail`, `version_check`, `calendar`, `worker`.
- Keep all earlier domain and registration checks.
- Do not alter authentication, provisioning, mail, calendar, version checking, or worker production logic if the new F401 gate finds no violations.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: newly written and existing integration-adapter Python code must have no unused imports.

## Impact
GitHub Actions CI workflow, OpenSpec and implementation plan. No application/API/database/role behavior changes.
