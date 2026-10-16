# Inline-edit inventory (implementation audit, 2026-10-13)

This list covers Vue tabular surfaces under `services/frontend/src/views` and
`services/frontend/src/components`. Columns are classified against the backend
contracts, not against whether an input could technically be rendered. A cell is
**not editable** unless its endpoint has an authoritative conditional write and
the domain's permission/confirmation rules can be preserved.

| Surface | Columns | Classification and mutation contract | Status |
| --- | --- | --- | --- |
| EventListView list / mobile cards | Title | Scalar, planner in event district, internal active slot; `PATCH /api/v1/events/{id}/inline` with `If-Match` | **Integrated** |
| EventListView list | Start | Date/time moved together with the end (duration kept); `PATCH /api/v1/events/{id}` with mandatory `If-Match` (428/412), atomic minister revalidation on the server; WARN conflicts need one explicit confirmation, BLOCK/412 stay in the cell. Not offered for invitation copies, external or cancelled events | **Integrated** (desktop table; mobile cards keep the edit dialog) |
| EventListView list | Category, congregation (Zuordnung) | Duties are never deleted; they are flagged for review or hidden from the new scope on read. Inline change first runs `POST /api/v1/events/{id}/change-impact` (now incl. `category` and `duties_newly_flagged` / `duties_quarantined_after`), BLOCK refuses, flagged duties or WARN need one explicit confirmation, then `PATCH` with `If-Match`. Not offered for holidays (generated), invitation copies, external or cancelled events | **Integrated** (desktop table; mobile cards keep the edit dialog) |
| EventListView list / mobile cards | Responsible | Assignment via `PUT /api/v1/service-assignments/inline` with `If-Match` (428/412), WARN acknowledgement once; clearing/deleting remains in the dialog | **Integrated** (PR #577) |
| EventListView list | District, invitation, type, source | Derived, tenancy metadata, cross-scope or external authority | Read-only |
| EventListView list | Status, approval | Cancellation/release workflow with existing confirmation and irreversible transitions | Action/workflow |
| EventListView list | Edit action | Opens domain modal, including destructive confirmation | Action |
| LeadersAdminView leaders table / cards | Name, email, phone | Scalar/contact via `PATCH /api/v1/districts/{district_id}/leaders/{leader_id}/inline` with `If-Match` and planner role | **Integrated** |
| LeadersAdminView leaders table / cards | Grade, special role, home congregation | Plain appointment attributes; the leader's congregation does not enter any assignment conflict rule. `PATCH .../leaders/{id}/inline` with `If-Match` (428/412), tenant check for the congregation, PLANNER role. Grade cannot be cleared | **Integrated** |
| LeadersAdminView leaders table / cards | Active state | Lifecycle: DISTRICT_ADMIN only (enforced server-side, edit hidden otherwise); advisory lock shared with assignment eligibility; deactivation needs an explicit confirmation, future assignments are kept and flagged for review | **Integrated** |
| LeadersAdminView leaders | Notes, user link, list visibility, service end date | Workflow/identity fields; remain in the edit dialog | Action/workflow |
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
