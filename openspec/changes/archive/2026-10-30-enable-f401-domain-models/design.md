## Context
PR #720 introduced a passing isolated F401 gate for the registration domain model, public registration router, domain ports, domain planning and domain services. A repository-wide F401 toggle remains risky, notably for intended exports.

## Decision
Expand that same pinned Ruff command to the entire `app/domain/models` package rather than a handwritten allow-list. This includes new model modules automatically and preserves the existing paths. Remove only `Enum` from five `from enum import Enum, StrEnum` declarations; their subclasses inherit from `StrEnum`.

## Test evidence (RED)
On initial head `d09555b`, GitHub Actions [run 40030528685](https://github.com/stritti/nak-district-planner/actions/runs/40030528685) failed precisely at `Incremental F401 unused-import gate for reviewed modules`, listing five unused `enum.Enum` imports in `export_token.py`, `invitation.py`, `leader.py`, `membership.py` and `service_assignment.py`.

## GREEN and broader verification
Re-run that exact gate after removing the five imports; require backend unit and PostgreSQL RLS integration suites, >=80% backend coverage, Ruff project lint, frontend CI, OpenSpec strict validation and security checks to pass. No speculative test-pass claim until CI reports completion.

## Release risk and scope
No change to runtime imports or API contracts is intended. `models/__init__.py` uses explicit `__all__` and is left untouched. Future work under #715 covers application, adapters and test modules before removing the global F401 ignore.
