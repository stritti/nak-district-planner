# Implementation Roadmap

This document defines the prioritized implementation order for all major
approved architectural changes. It ensures safe sequencing and minimizes
cross-cutting refactor risks.

---

## Guiding Principle

1. Structural domain foundations first.
2. Security guardrails second.
3. Sync stabilization third.
4. Hardening and non-functional concerns last.

Behavioral changes must follow this order unless explicitly re-approved.

---

## Phase 1 – Planning Model Refactor

Change: `planning-slot-hybrid-sync`

Detailed technical plan:
- `openspec/architecture/phase-1-planning-model-technical-plan.md`

Scope:
- Introduce PlanningSeries
- Introduce PlanningSlot (Aggregate Root)
- Introduce EventInstance
- Migrate legacy Event model
- Keep existing sync logic temporarily

Feature Flag:
- `USE_PLANNING_SLOT_MODEL`

Risk Level: HIGH
Priority: 🔴 Critical Foundation

---

## Phase 2 – RBAC Introduction

Change: `introduce-rbac-permissions-model`

Scope:
- Role and Membership model
- Authorization guards in application layer
- Protect planning and integration use cases

Risk Level: MEDIUM
Priority: 🔴 Critical Governance

---

## Phase 3 – Sync Metadata Stabilization

Change: `harden-calendar-sync-algorithm` (partial)

Scope:
- Introduce sync_state fields
- Add ExternalEventLink table
- Persist hashes and revision markers
- Collect metadata without altering behavior

Feature Flag:
- `USE_SYNC_METADATA`

Risk Level: MEDIUM
Priority: 🟠 Structural Preparation

---

## Phase 4 – Hardened Sync Engine Activation

Change: `harden-calendar-sync-algorithm` (full activation)

Scope:
- Activate state machine
- Enforce idempotency
- Enable loop prevention
- Enable delete behavior modes

Feature Flag:
- `USE_HARDENED_SYNC_ENGINE`

Risk Level: HIGH
Priority: 🔴 Core Integrity

---

## Phase 5 – Non-Functional Baseline Enforcement

Change: `introduce-non-functional-baseline`

Scope:
- Audit log infrastructure
- Encryption enforcement
- Rate limiting
- Retry & backoff
- Performance validation

Risk Level: MEDIUM
Priority: 🟡 Hardening

---

## Estimated Timeline (1–2 Developers)

- Phase 1: 1–2 weeks
- Phase 2: 1 week
- Phase 3: 1 week
- Phase 4: 1–2 weeks
- Phase 5: 1 week

Total: ~5–7 weeks

---

## Migration Strategy Requirement

Before executing Phase 1 in production:
- Perform staging migration with snapshot.
- Validate data integrity.
- Prepare rollback strategy.

No phase should begin before the previous one is stable.

---

End of Implementation Roadmap
