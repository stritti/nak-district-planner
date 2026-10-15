# Inline-edit inventory (implementation audit, 2026-10-13)

This list covers Vue tabular surfaces under `services/frontend/src/views` and
`services/frontend/src/components`. Columns are classified against the backend
contracts, not against whether an input could technically be rendered. A cell is
**not editable** unless its endpoint has an authoritative conditional write and
the domain's permission/confirmation rules can be preserved.

| Surface | Columns | Classification and mutation contract | Status |
| --- | --- | --- | --- |
| EventListView list / mobile cards | Title | Scalar, planner in event district, internal active slot; `PATCH /api/v1/events/{id}/inline` with `If-Match` | **Integrated** |
| EventListView list | Start | Date/time plus duration and minister/duty validity, dependent atomic change; `PATCH /api/v1/events/{id}` has no mandatory version | **Deferred** |
| EventListView list | Category, congregation | Scope changes require reassessing/quarantining assignments; legacy `PATCH /api/v1/events/{id}` lacks the complete duty-review workflow | **Deferred** |
| EventListView list | Responsible | Assignment create/update/delete, warning acknowledgment and deletion confirmation, must use `/api/v1/events/{id}/assignments`; no end-to-end conditional-write path yet | **Deferred** |
| EventListView list | District, invitation, type, source | Derived, tenancy metadata, cross-scope or external authority | Read-only |
| EventListView list | Status, approval | Cancellation/release workflow with existing confirmation and irreversible transitions | Action/workflow |
| EventListView list | Edit action | Opens domain modal, including destructive confirmation | Action |
| LeadersAdminView leaders table / cards | Name, email, phone | Scalar/contact via `PATCH /api/v1/districts/{district_id}/leaders/{leader_id}/inline` with `If-Match` and planner role | **Integrated** |
| LeadersAdminView leaders table / cards | Grade, special role, home congregation, active state | Appointment, identity, scope and lifecycle semantics; not editable through the scalar inline contract | **Deferred** |
| LeadersAdminView registrations table | Name, email, grade, requested congregation, status, submission date | Review/registration acceptance state, not independently mutable scalar cells | Read-only/workflow |
| LeaderUnavailabilityList | Leader, dates, reason, note | Unavailability records use explicit add/remove; no safe conditional PATCH | Read-only/workflow |
| MatrixTable | Congregation and date | Row header and chronological context | Read-only |
| MatrixTable | Assignment, leader, event metadata, deviation, invitation | Assignment actions open the conflict-aware modal; certain cells are forwarded/host-owned, assignment endpoint lacks required strong conditional revision | **Deferred** |
| MatrixTable | Empty/gap cell | Opens existing assignment modal; conflict/confirmation semantics must remain | Action/workflow |

The rest of the Vue views/components have no semantic `<table>` element;
their standalone cards and editor dialogs are not separate table surfaces.
The event week/month calendars are grid and pill navigation displays,
not ordinary inline-edit table cells, and retain their detail-dialog action.

## Guardrails

- A missing event or leader revision suppresses the edit affordance; never silently use a blind PATCH.
- External, cancelled or out-of-district events are not inline editable.
- The new event-inline endpoint only accepts `title` and `description`;
  other fields receive 422 until the relevant domain-specific safe workflows exist.
- Remaining administrative and assignment columns are outstanding per tasks 1.2, 2.4, 3.3 and 4.3-4.6.
- This document is an inventory, **not** a claim that OpenSpec PR #530 has been fully implemented.
