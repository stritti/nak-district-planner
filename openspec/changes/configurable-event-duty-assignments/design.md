## Context

The canonical event aggregate uses `PlanningSlot` for the planning identity and `EventInstance` for actual timing. The existing `service_assignments` uniqueness constraint is intentionally limited to a single liturgical service leader per slot. Organisational duties must not be inserted into or constrained by this table. Calendar export uses stable slot-based UIDs and differentiated public/internal/personal visibility.

## Decisions

### 1. Separate configurable roles and assignments

Introduce domain concepts `EventDutyCategory` (district-owned or congregation-owned definition), `EventTypeDutyConfiguration` (applicability and local enabled/disabled override) and `EventDutyAssignment` (planning_slot_id, duty_category_id, person/user reference). Use stable opaque IDs for references, a normalised code for idempotent system defaults, and display labels stored independently of identity. Apply district scoping and foreign-key constraints. Make `(planning_slot_id, duty_category_id, person_id)` unique. Assignment cardinality defaults to one person per duty; support a configurable positive capacity to allow multiple persons if a duty requires it. No person assignment is mandatory.

### 2. Deterministic scope precedence

District definitions form the inherited base for congregation slots. A congregation override may enable, disable or replace the applicability/capacity for a district-defined role; congregation-owned roles are additional. Explicit overrides win over inherited district settings; no override follows current district configuration. District-level slots use district configuration, not an arbitrary congregation's override. Apply the exact stored event category; `Gottesdienst` gets the three defaults, all other event categories get only Schließdienst unless explicitly configured. Materialise default catalogue entries idempotently for existing/new districts without assigning people. Configuration edits affect future available choices but do not delete stored historical assignments.

### 3. Preserve domain boundaries

Attach organisational assignments to `PlanningSlot`, not `EventInstance`, so imported event-instance timing changes do not orphan duties. Event display resolves start/end using the same slot-instance precedence as existing calendars. Deletion/cancellation follows existing planning visibility and lifecycle rules. This feature neither extends nor relaxes `service_assignments.planning_slot_id` uniqueness or leader-conflict rules. Avoid N+1 reads by batching assignment views for event lists and feeds.

### 4. Authorisation and participant identity

Only `DISTRICT_ADMIN` may modify district catalogue/configuration; `CONGREGATION_ADMIN` may modify configuration for that congregation only. A `PLANNER` with the relevant scoped authority may manage assignments on events they can edit. User/person references must resolve to valid selectable members of the same district with an authorised relationship to the event scope; never use arbitrary email addresses or raw free text. Apply row-level tenant isolation and identical non-disclosing errors for unknown/out-of-scope references. Personal calendar access relies on authenticated subject or existing opaque personal token, not a guessed person ID.

### 5. Calendar projection, not duplicate events

For a person assigned several duties on the same slot, display one calendar entry including all task labels; use the existing `{planning_slot_id}@nak-bezirksplaner` UID where applicable. Add duty information only to that person's authenticated personal view or personal opaque-token ICS. A duty assignment alone qualifies the event for that person's personal calendar. Preserve existing leader-based entries and combine labels when the person is both leader and duty holder. Public/congregation feeds must not expose names or personal responsibilities from this feature. Updates, removal and cancellation must change the next feed response and the calendar view deterministically. Do not create provider-side copies.

## Risks and mitigations

- **Inheritance ambiguity**: record explicit overrides and test district changes before/after local override.
- **Privacy**: restrict task/person fields to appropriately authenticated/scoped views; test cross-tenant access and token types.
- **Historical integrity**: disable rather than hard-delete used categories; preserve assignment display labels or immutable catalogue records.
- **Scheduling**: keep existing leader conflict checks unchanged; explicitly document duty overlap policy as non-blocking for MVP, with optional warnings only.
- **Release safety**: additive migration and idempotent seeding; test upgrade against existing slots, rollback, concurrency and default inserts.

## Open Questions

None blocking. The MVP deliberately allows concurrent organisational duty appointments rather than introducing implicit hard conflict rules for volunteers.
