# F401 domain-model expansion plan (#715)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and test-driven-development for this plan.

**Goal:** Extend CI's unused-import checks to every domain model module without changing domain behavior.

**Architecture:** Extend the existing isolated Ruff F401 command to include the complete `app/domain/models` directory, preserving its earlier checked modules. Resolve only demonstrated violations; no repo-wide ignore removal.

**Tech Stack:** Python >=3.14, Ruff pinned by uv.lock, GitHub Actions, OpenSpec spec-driven.

**Spec:** openspec/changes/enable-f401-domain-models/specs/ci-quality-gates/spec.md

## Global constraints
- Retain Clean Code and architectural behavior.
- Backend test coverage >80%; include exceptions and PostgreSQL RLS tests.
- Preserve any explicitly listed domain reexports and existing imports at runtime.

## Review focus
- `models/__init__.py` explicit `__all__` should not lose exports.
- Newly introduced model files must automatically fall under the gate.
- Previous checked domain port/planning/service paths remain protected.
- Ruff in CI must fail as intended for unused imports.
- Import-only changes must not affect OIDC/Pydantic/SQLAlchemy and public API behavior.

## Tasks
- [x] **RED:** expand isolated F401 CI gate and observe five errors in run 40030528685.
- [x] **GREEN implementation:** remove exactly the five reported `enum.Enum` imports.
- [ ] Verify the exact gate passes, as well as backend unit/integration/coverage >80%, lint and docs.
- [ ] Request Codex review and update issue #715 for the next subset.
