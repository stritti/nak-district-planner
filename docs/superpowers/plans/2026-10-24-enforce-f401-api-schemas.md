# API schema Ruff F401 expansion — implementation plan (#715)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and test-driven-development where production changes are needed.

**Goal:** Enforce F401 in every existing and future API Pydantic schema module while preserving runtime validation.

**Architecture:** Extend the existing isolated CI Ruff check with one complete directory. Do not touch schema imports when lint already passes; keep all earlier F401 targets.

**Tech Stack:** Python 3.14, pinned Ruff, FastAPI/Pydantic, GitHub Actions, OpenSpec.

**Spec:** openspec/changes/enforce-f401-api-schemas/specs/ci-quality-gates/spec.md

## Risk boundaries
- No runtime imports, decorators or validation models touched.
- Backend coverage >80%, existing unit and PostgreSQL RLS integration tests including failure paths.
- Preserve earlier domain/application/adapter checks and Security Scans.
- No broad `noqa` suppressions or global ignore removal yet.

## Review focus
- Entire `schemas` directory checked, not a handpicked list.
- Newly introduced schema files are protected automatically.
- Previous registration, domain, application and six integration adapter paths remain checked.
- CI's isolated F401 semantics proven by previous RED tests (issue #715).
- No Pydantic runtime semantics or API contract changes.

## Tasks
- [x] Activate schema directory scope.
- [x] Verify first gate success on CI 40098618093.
- [ ] Run full fresh CI on final head, obtain independent Codex review and update issue.
