# Expand Ruff F401 to integration adapters — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and test-driven-development while implementing.

**Goal:** Enforce F401 for every module in six integration adapter packages without modifying runtime behavior.

**Architecture:** Extend the existing isolated Ruff check with complete directories so current and future modules inherit the quality gate. Preserve the global ignore until remaining API/DB/test modules are triaged.

**Tech Stack:** Python 3.14, uv-locked Ruff, GitHub Actions, OpenSpec.

**Spec:** openspec/changes/enable-f401-integration-adapters/specs/ci-quality-gates/spec.md

## Global constraints
- Preserve existing OIDC, RBAC, SMTP and asynchronous worker behavior.
- Keep backend coverage strictly >80% and verify PostgreSQL/RLS integration.
- No broad `noqa`, no security CI bypasses and no unrelated dependency changes.

## Review focus
- Intentional integration module imports and module-level exports.
- Negative F401 regression: an unused import in a new adapter must fail CI.
- Keeping all domain and registration paths in the gate.
- No hidden behavior change in authentication, mail or worker exception handling.
- Dependency security issue #723 remains tracked separately.

## Tasks
- [x] Identify six adapter packages (33 Python files).
- [x] Append paths to isolated CI check and see zero F401 findings on initial run 40087353556.
- [ ] Verify full backend coverage, frontend, OpenSpec and security baseline status.
- [ ] Obtain independent Codex review and update #715.
