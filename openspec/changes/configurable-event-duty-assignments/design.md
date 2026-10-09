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

Only `DISTRICT_ADMIN` may modify district catalogue/configuration; `CONGREGATION_ADMIN` may modify configuration for that congregation only. A `PLANNER` with the relevant scoped authority may manage assignments on events they can edit. Linked user/person references must resolve to valid selectable members of the same district with an authorised relationship to the event scope; name-only organisational duty participants are allowed under the scoped remembered-name policy below, but arbitrary emails or fabricated user identities are not. Apply row-level tenant isolation and identical non-disclosing errors for unknown/out-of-scope references. Personal calendar access relies on authenticated subject or existing opaque personal token, not a guessed person ID.

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

### 6. Typed remembered names and optional linked identities

Organisational duty entries accept either an eligible linked user/person reference or a validated name-only participant. Do not require an account or invent a linked identity for a text name. Persist a separate, tenant-scoped `DutyNameSuggestion` (normalised name/display name, duty category ID and owning district/congregation scope, active/hidden state) and reference its stable ID from name-only assignments where useful; preserve an immutable assignment display-name snapshot. Autocomplete matches the selected organisational duty category, not merely the event category: a name remembered as Organist is not suggested as Schließdienst until entered there as well. Resolve suggestions using the event's effective congregation/district scope; do not leak other tenants' suggestions. Exact duplicates (case/whitespace-normalised) must be prevented within the same scope/category. A name can be re-entered after suppression as a deliberate new activation, but a suppressed suggestion MUST NOT reappear automatically because old assignments are displayed or imported. Deleting a suggestion means soft suppression from new choices, never erasing name-only assignment history. For calendar access, only verified linked user identities can receive personal calendar entries; unlinked plain text names are displayed on the event, but never gain an account, feed or access token implicitly.

### 7. Minister lifecycle and service eligibility

Keep minister/service-leader records and referential keys permanently when deactivating or removing them from normal visible lists. Model `is_active` and optional `service_end_date` (local calendar date, inclusive); a separate `hidden_from_lists` state implements reversible frontend list removal without a database DELETE. Existing references and historical assignments remain resolvable in privileged historical/event views. Normal current-person pickers and list APIs exclude deactivated/hidden persons by default, with an authorised explicit include-inactive option for administration and historical inspection. On assignment or reassignment, evaluate both active/hidden state and the target slot's local planning date; do not offer or accept new services after `service_end_date`, even if the person is otherwise marked active. When planning before/on the end date, a not-yet-ended active person remains eligible. A status change or end-date update flags already scheduled future conflicting assignments to planners for review without silently deleting them. Existing leader double-booking and tenant checks remain intact; server-side eligibility checks are authoritative for all write APIs, including bulk/matrix workflows. Restore/reactivation must be authorised and audited.

### 8. Compatibility and rollout

Add separate management APIs for scoped autocomplete suggestions and lifecycle changes to existing leader/member management, with RBAC and RLS. Provide additive migrations and existing-record defaults (active, visible, no end date). Do not equate hiding from frontend lists with irrecoverable deletion. Test historical exports, suggestion suppression, concurrent duplicate-name creation, calendar projection limits for name-only participants, date/time-zone boundaries and all assignment entry points.
