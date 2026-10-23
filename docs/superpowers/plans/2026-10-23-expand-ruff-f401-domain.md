# Expand Ruff F401 to domain modules — implementation plan (#715)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and test-driven-development to implement each task.

**Goal:** Require Ruff F401 for all domain planning rules, repository ports and domain services without changing runtime contracts.

**Architecture:** Expand the existing isolated CI gate to all files in three coherent directories; resolve true F401 findings only, preserving documented intentional exports.

**Tech Stack:** Python 3.14, Ruff pinned via uv.lock, GitHub Actions, OpenSpec.

**Spec:** openspec/changes/expand-ruff-f401-to-domain-modules/specs/ci-quality-gates/spec.md

## Global constraints
- Keep total code coverage >80%.
- Preserve current public APIs, SQLAlchemy/RLS and application behavior.
- No unsafe blanket noqa or global F401 switch before full audit.

## Review Focus
- External users importing repository-port enum names should not break.
- New modules in protected directories should be checked automatically.
- Prior registration-module F401 checks must not regress.
- CI's isolated Ruff should actually fail for unused imports.
- No database/RLS behavior changes.

## Tasks
- [x] **T1 RED:** CI run 40028745839 failed F401 as expected on `30f4bf0`: `NotificationType` and `EventApprovalStatus` were unused in `domain/ports/repositories.py`.
- [x] **T2 GREEN implementation:** remove only the two diagnosed unused imports; verify the identical gate in the new PR head's GitHub Actions.
- [ ] **T3:** validate OpenSpec and full backend/integration coverage, request a Codex review.
