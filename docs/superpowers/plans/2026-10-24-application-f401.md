# Application-wide Ruff F401 expansion plan — #715

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and test-driven-development when implementing this plan.

**Goal:** Enforce unused-import checks across all application modules while preserving CSRF and calendar import behavior.

**Architecture:** Expand the preexisting CI `ruff check --isolated --select F401` invocation to `app/application`; remove exactly the reported unused imports. Do not change business logic.

**Tech Stack:** Python >=3.14, uv-locked Ruff, GitHub Actions, FastAPI/SQLAlchemy, OpenSpec.

**Spec:** openspec/changes/enable-f401-application-services/specs/ci-quality-gates/spec.md

## Global constraints
- Keep >80% backend coverage and critical router coverage >=80%.
- Test fail-closed CSRF paths and PostgreSQL RLS integration using existing suites.
- Preserve previous F401 gates and avoid blanket `noqa`.

## Review focus
- CSRF token integrity, expired/invalid token handling.
- Holiday service still maps to PlanningSlots, not EventInstances.
- All existing imports from earlier F401 phases remain guarded.
- New files in application/ are checked automatically.
- Runtime import side effects and public API contracts remain stable.

## Tasks
- [x] **RED:** CI run 40086639329 failed on five unused imports after application-wide F401 gate was added.
- [x] **GREEN implementation:** remove exactly those five unused imports.
- [ ] Verify the same CI gate passes on the next head; confirm complete integration/coverage workflows.
- [ ] Request Codex review, reconcile findings and update #715.
