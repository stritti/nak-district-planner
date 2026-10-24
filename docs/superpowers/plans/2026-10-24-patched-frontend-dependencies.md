# Remediate Happy DOM and fast-uri advisories — implementation plan (#723)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development for the individual steps.

**Goal:** Restore the mandatory frontend dependency audit without suppressing vulnerabilities.

**Architecture:** Upgrade only two affected packages in the frontend manifest and its Bun lock, preserve the frozen-lock CI process and add a regression specification. No runtime source changes.

**Tech Stack:** Bun 1.4.2, Vue/Vitest/Happy DOM 21, Vite/PWA, GitHub Actions, OpenSpec.

**Spec:** openspec/changes/fix-frontend-dependency-advisories-723/specs/ci-quality-gates/spec.md

## Global constraints
- Do not lower `bun audit --audit-level=moderate` or add vulnerability allowlists.
- Preserve frontend unit/E2E coverage gates, lint and PWA build.
- Keep backend code unchanged; backend coverage >80%.
- Document full SHA512-integrity updates in the lock.

## Review focus
- Happy DOM 21 major-version compatibility with Vitest 5.
- Up-to-date `fast-uri` in all transitive resolution paths.
- Frozen lockfile integrity/checksum and metadata correctness.
- Negative audit scenarios must continue to block CI.
- No reliance on root docs lock instead of `services/frontend/bun.lock`.

## Tasks
- [x] **RED:** Confirm CI #40086580700 fails due to locked vulnerable versions.
- [x] **GREEN implementation:** bump Happy DOM range and both frontend lock resolutions.
- [ ] Run the mandatory security audit, frozen installation, Vitest and full CI; fix actual regressions.
- [ ] Request independent Codex review, update PR and issue, obtain green main after merge.
