## Context

The district planner currently treats congregations as a flat collection in both administrative overview and matrix planning contexts. This limits readability when districts contain many congregations that are naturally organized by region or ministry structure. The reported workflow also indicates a setup gap: creating a district or congregation does not expose all key options in one place, which leads to immediate follow-up edits and inconsistent initial records.

The change spans backend and frontend concerns: data modeling for optional congregation grouping, API exposure, grouped rendering in multiple views, and UX updates for creation dialogs. Existing installations already contain districts and congregations, so the design must preserve compatibility while enabling incremental adoption.

## Goals / Non-Goals

**Goals:**
- Introduce an optional group assignment for congregations that can drive visual grouping in district/congregation overview screens.
- Provide optional grouping/sorting by group in the matrix view without breaking existing default ordering.
- Ensure congregation and district creation flows present all relevant options directly in the initial dialog.
- Keep data migration safe and backward compatible for records without group assignment.

**Non-Goals:**
- Reworking service-assignment business rules or matrix cell logic beyond ordering/group presentation.
- Introducing role-based visibility rules for groups in this change.
- Building a separate standalone group-management module with advanced permissions.

## Decisions

### Decision: Add a first-class, optional congregation group entity tied to district scope
Groups are modeled as district-scoped entities, and congregations reference a nullable group identifier.

Rationale:
- District-level scope aligns with current tenant hierarchy (district -> congregation).
- Nullable reference allows existing data and small districts to keep current behavior.
- Structured grouping enables deterministic ordering and reusable labels across views.

Alternatives considered:
- Free-text group field on congregation only: rejected due to typo drift and inconsistent grouping labels.
- Global groups across districts: rejected because groups are organizationally district-specific.

### Decision: Keep default matrix ordering and add opt-in secondary grouping/sorting mode
The matrix keeps its current baseline sort. A user-selectable mode applies grouping by congregation group, then existing congregation order within each group.

Rationale:
- Preserves expected behavior for current users and avoids surprise regressions.
- Supports the requested "optional as additional sorting" behavior.

Alternatives considered:
- Always-on grouping: rejected because it changes baseline UX and may hurt small districts.
- Separate grouped matrix page: rejected due to duplication and higher maintenance cost.

### Decision: Expand create dialogs to include full option set at creation time
District and congregation creation dialogs will present all required and optional fields immediately, including group assignment for congregation where applicable.

Rationale:
- Removes post-create edit loop and improves data completeness at entry.
- Fits user request for direct dialogs with all options.

Alternatives considered:
- Keep minimal create + advanced edit flow: rejected due to current friction.
- Multi-step wizard: rejected as unnecessary complexity for currently scoped fields.

### Decision: Roll out with additive schema/API changes and null-safe defaults
Backend schema changes are additive; API responses include group metadata when available. Requests without group remain valid.

Rationale:
- Minimizes risk for existing clients and allows incremental frontend rollout.
- Supports zero-downtime deployment patterns.

Alternatives considered:
- Mandatory group assignment: rejected because it would require immediate data backfill and block create flows.

## Risks / Trade-offs

- [Grouping semantics become unclear across districts] -> Mitigation: enforce district scoping and validate group-to-congregation district consistency in service layer.
- [UI complexity increases in matrix and overview] -> Mitigation: keep grouping optional, default off, and use concise grouped section headers.
- [Migration errors for legacy records] -> Mitigation: nullable foreign key, idempotent migration script, and fallback rendering for null groups.
- [API consumers ignore new fields] -> Mitigation: additive response fields only; no required request breaking changes.

## Migration Plan

1. Add congregation-group table and nullable congregation.group_id column via migration.
2. Deploy backend with compatibility logic (accept/create without group, return optional group payload).
3. Deploy frontend grouped rendering and create-dialog enhancements behind default-safe behavior.
4. Optionally seed initial groups per district from admin UI or scripts after deployment.
5. Rollback strategy: frontend can ignore grouping mode; backend can continue operating with null group_id values if group usage is disabled.

## Open Questions

- Should districts be creatable with predefined congregation groups in the same dialog, or only district-level options while groups are added afterward?
- Does the matrix require persistent user preference for grouping mode (per user/per district) in this phase, or session-only toggle?
