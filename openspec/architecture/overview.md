# NAK District Planner – Architecture Overview

This document provides a high-level architectural overview of the system.
It complements OpenSpec changes and serves as the stable mental model for
understanding the domain and system boundaries.

---

## 1. Architectural Style

The system follows a **Hexagonal (Ports & Adapters) Architecture**.

Core principles:
- Domain logic is framework-independent.
- Application layer orchestrates use cases.
- Adapters handle HTTP, persistence, background jobs, and external calendars.
- External systems never directly influence domain structure.

```
          ┌────────────────────────────┐
          │        External World      │
          │  (Google, Outlook, ICS)    │
          └──────────────┬─────────────┘
                         │
                  ┌──────▼──────┐
                  │  Adapters   │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │ Application │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │   Domain    │
                  └─────────────┘
```

---

## 2. Core Domain Model

### 2.1 Planning Model (Soll/Ist Separation)

The system distinguishes between planned structure (Soll) and actual execution (Ist).

```
PlanningSeries
   └── PlanningSlot (Aggregate Root)
         ├── EventInstance (actual execution)
         ├── ServiceAssignments
         └── SyncMetadata
```

- **PlanningSeries**: Template for recurring services.
- **PlanningSlot**: Normative calendar position (matrix anchor).
- **EventInstance**: Real-world execution time and sync state.
- **ServiceAssignment**: Assigned roles/persons for the slot.

Matrix rendering is based solely on `PlanningSlot`.

---

### 2.2 Synchronization Model

Synchronization is hybrid and governance-aware.

#### Field Authority

- STRUCTURAL fields → internally authoritative.
- SOFT fields → externally editable.
- Time changes → stored as deviation.

#### Sync State Machine

EventInstance contains:
- CLEAN
- DIRTY_INTERNAL
- DIRTY_EXTERNAL
- CONFLICT

External mapping uses `ExternalEventLink`.
New external events become `ExternalEventCandidate` until reviewed.

---

### 2.3 Governance Model (RBAC)

Role-based access control is scoped.

```
User
  └── Membership
        - role
        - scope_type (DISTRICT | CONGREGATION)
        - scope_id
```

Canonical roles:
- DISTRICT_ADMIN
- CONGREGATION_ADMIN
- PLANNER
- VIEWER

Authorization is enforced in the application layer.

---

### 2.4 Notifications

Governance-relevant events (e.g., external event detection)
produce persistent in-app notifications.

Notifications:
- Stored in database
- Visible until read or dismissed
- Scoped by district or congregation

---

## 3. Non-Functional Baseline

The system enforces:

- Performance baseline (e.g., matrix ≤ 500ms under district-scale load)
- Encryption of external credentials at rest
- Secure export tokens (≥128-bit entropy)
- Audit logging for governance actions
- Exponential backoff for sync failures
- Rate limiting for public endpoints

---

## 4. Multi-Tenancy Model

The system is district-centric.

```
District
  └── Congregation
```

All planning, sync, permissions, and exports are scoped to a district.

Isolation strategy:
- Shared schema
- Scoped by district_id
- Authorization ensures cross-district isolation

---

## 5. System Principles

1. Planning is authoritative.
2. External systems cannot silently mutate structure.
3. All governance-relevant actions are auditable.
4. Sync must be deterministic and idempotent.
5. Domain integrity is more important than convenience.

---

## 6. Evolution Strategy

The system evolves strictly via OpenSpec changes:

Change → Proposal → Design → Specs → Tasks → Apply → Archive

This document is stable context.
Behavioral changes must always be introduced through a formal change.

---

## 7. Aggregate Boundaries & Transaction Rules

`PlanningSlot` is the primary Aggregate Root.

Rules:
- `EventInstance`, `ServiceAssignment`, and `SyncMetadata` MUST only be modified via `PlanningSlot`.
- No repository SHALL expose direct mutation of `EventInstance` without aggregate validation.
- `ExternalEventLink` MUST always reference an existing `PlanningSlot`.
- `EventInstance` MUST NOT exist without a `PlanningSlot`.

All transactional consistency for planning-related data is enforced at the aggregate boundary of `PlanningSlot`.

---

## 8. Entity Lifecycle Rules

### PlanningSeries
- Created by authorized roles.
- Generates `PlanningSlot` instances (rolling window).
- Deactivation does NOT delete historical slots.

### PlanningSlot
- Created via PlanningSeries generation or explicit planning action.
- May be soft-deleted (CANCELLED).
- Hard deletion is restricted and auditable.

### EventInstance
- Created automatically alongside PlanningSlot.
- Cannot outlive its PlanningSlot.

### ExternalEventCandidate
- Created only by sync engine.
- Must transition to MAPPED or IGNORED.
- Cannot directly mutate planning structure.

### Notification
- Created by domain events.
- Persists until read or dismissed.

---

## 9. Data Integrity & Consistency Constraints

- All entities are scoped by `district_id`.
- Cross-district references are forbidden.
- Unique constraint on `(provider, external_event_id)` in `ExternalEventLink`.
- Soft deletion preferred over hard deletion for governance entities.
- Referential integrity enforced at database level.

---

## 10. Domain Event Strategy

The system uses explicit domain events for cross-cutting concerns.

Examples:
- `PlanningSlotModified`
- `ExternalEventDetected`
- `SyncStateChanged`

Domain events:
- Trigger audit logging
- Trigger notification creation
- Decouple sync side effects from core logic

Domain events are emitted within the application layer after aggregate state transitions.

---

## 11. Privacy & Data Retention

The system handles personal data (e.g., ServiceAssignments).

Principles:
- Data minimization (store only necessary personal data).
- Encryption for sensitive credentials.
- Audit logs are immutable but may be archived.
- Export tokens are revocable.

Future change may define explicit retention periods.

---

## 12. Explicit Out-of-Scope

The system intentionally does NOT:

- Implement full multi-master CRDT synchronization.
- Provide real-time collaborative editing.
- Act as a full church ERP system.
- Support cross-district shared planning.

Scope expansion must be introduced via formal OpenSpec change.

---

End of Architecture Overview
