# Inline-edit inventory (completed 2026-10-16)

This list covers every Vue table, list-style overview and planning matrix in
`services/frontend/src`. Each column is classified against the backend contract,
not against whether an input could technically be rendered. A cell is **not
editable** unless its endpoint has an authoritative conditional write (`If-Match`,
428 without, 412 if stale) and the domain's permission and confirmation rules
are preserved. Backend enforcement is always authoritative; the UI hides the
editor when the user lacks the role or the row carries no revision.

Legend: **Integrated** = shared `InlineEditableCell` with conditional write.
**Read-only** = derived or externally owned. **Action/workflow** = explicit action,
dialog or confirmation, deliberately not a cell editor. **Excluded** = documented
reason below.

## Tables

| Surface | Columns | Classification and mutation contract | Status |
| --- | --- | --- | --- |
| EventListView list / mobile cards | Title | `PATCH /api/v1/events/{id}/inline` with `If-Match`; planner in event district, internal active slot | **Integrated** |
| EventListView list / mobile cards | Start | Date/time moved with the end (duration kept); `PATCH /api/v1/events/{id}` with `If-Match`; atomic minister revalidation; WARN needs one explicit confirmation, BLOCK/412 stay in the cell | **Integrated** |
| EventListView list / mobile cards | Category, congregation (Zuordnung) | Duties are never deleted; flagged for review or hidden from the new scope on read. `POST …/change-impact` previews, one confirmation, then `PATCH` with `If-Match` and `acknowledged_duty_impact`; the server recomputes the impact under the slot lock and answers 409 `duty_impact_unacknowledged` if more would be affected. Not offered for generated holidays | **Integrated** |
| EventListView list / mobile cards | Responsible | `PUT /api/v1/events/{id}/assignments/inline` with `If-Match`, WARN acknowledged once; clearing stays in the dialog | **Integrated** |
| EventListView list | District, invitation, type, source | Derived, tenancy metadata, cross-scope or external authority | Read-only |
| EventListView list | Status, approval | Cancellation/release workflow with confirmation and irreversible transitions | Action/workflow |
| EventListView list | Edit action | Opens the domain dialog. Its event update and assignment writes are conditional (`If-Match`; the assignment write uses the revision returned by the preceding event update) | Action |
| LeadersAdminView leaders table / cards | Name, e-mail, phone | `PATCH /api/v1/districts/{d}/leaders/{id}/inline` with `If-Match`; planner | **Integrated** |
| LeadersAdminView leaders table / cards | Grade, special role, home congregation | Plain appointment attributes; the leader's congregation enters no conflict rule. Same endpoint and revision; tenant check for the congregation; grade cannot be cleared | **Integrated** |
| LeadersAdminView leaders table / cards | Active state | Lifecycle: DISTRICT_ADMIN only (server and UI); advisory lock shared with assignment eligibility; deactivation needs `confirm_deactivation` (else 409), future assignments are kept and flagged for review | **Integrated** |
| LeadersAdminView leaders | Notes, user link, list visibility, service end date | Workflow/identity fields, remain in the edit dialog (which also sends `If-Match`) | Action/workflow |
| LeadersAdminView registrations table | Name, e-mail, grade, requested congregation, status, submitted | Registration review state; actions only open the approve/reject dialogs or the delete confirmation. Uses the shared table classes, no editor | Read-only / workflow |
| LeaderUnavailabilityList | Leader, period, reason, note | Records use explicit add and delete with confirmation; no scalar PATCH exists. Uses the shared table classes, no editor | Read-only / workflow |
| MatrixTable | Congregation, date | Row header and chronological context | Read-only |
| MatrixTable | Responsible (assignment) | Inline cell via `PUT …/assignments/inline` with the cell's `revision`; planner; hidden for invitation copies, host-managed and versionless cells. The assignment dialog (create, change, remove) sends the same revision | **Integrated** |
| MatrixTable | Event metadata, deviation, invitation, gap cells | Derived or opens the conflict-aware assignment dialog | Action/workflow |

## List-style overviews without a table

| Surface | Fields | Classification and reason | Status |
| --- | --- | --- | --- |
| DistrictsAdminView | District name | `PATCH /api/v1/districts/{id}` with `If-Match` and row lock; DISTRICT_ADMIN. Replaces the former ad-hoc rename input | **Integrated** |
| DistrictsAdminView | Group name | `PATCH /api/v1/districts/{d}/groups/{id}` with `If-Match` and row lock; DISTRICT_ADMIN. Replaces the former ad-hoc rename input | **Integrated** |
| DistrictsAdminView | Congregation (name, group, service times, invitation target) | Multi-field form with cross-field validation of the invitation target, edited in a dialog, never inline. Its PATCH is not conditional yet | **Excluded** (dialog; follow-up: revision) |
| ReminderConfigsPanel, EventHooksPanel | Active switch | Lifecycle switch: deactivation uses a dedicated endpoint, reactivation a PATCH; no text-cell interaction. Neither endpoint is conditional yet | **Excluded** (action; follow-up: revision) |
| ReminderConfigsPanel, EventHooksPanel | Day, time, subject, recipient, body | Multi-field forms with explicit save | **Excluded** (form) |
| DutySettingsView | Enabled, capacity, event types, labels | Settings form per duty category with one explicit Save for the atomic set | **Excluded** (form) |
| EventDutiesPanel (inside the event dialog) | Duty assignments | Add/replace/remove with confirmation and capacity rules; each write locks the slot row. Not conditional on the event revision | **Excluded** (dialog panel; follow-up: revision) |
| ExportTokensView | Tokens | Create, copy/open the feed URL, delete with confirmation; no editable scalar | Action/workflow |
| CalendarIntegrationsView | Integrations | Create, edit in a dialog, sync now, delete with confirmation | Action/workflow |
| ExternalCandidatesView | Candidates | Accept-and-create / dismiss review workflow | Action/workflow |
| RecurringEventsView | Monthly checklist | Accept/skip/reopen/resolve workflow with `template_revision`; selection checkboxes select, they do not edit | Action/workflow |
| RecurringEventsView | Templates | Edited in a form with `expected_revision` (409 `STALE_TEMPLATE`) | Action (conditional) |
| PersonalCalendarView, NotificationBell | Events, tokens, notifications | Derived, read-only | Read-only |

## Guardrails

- A missing event, leader, district or group revision suppresses the edit affordance; there is no blind PATCH fallback in the shared editor.
- External, cancelled, out-of-district events, invitation copies and generated holidays are not inline editable.
- The inline event endpoint only accepts `title` and `description`; other event fields go through the scoped `PATCH` flows above.
- Dialog and legacy writers of inline-editable fields are conditional on the same revision (event updates, assignment create/update/delete, leader updates, district and group renames).
- Read-only tables use the shared classes (`card`, `table-scroll`, `table-min-w`, `table-thead`, `table-th`, `table-td`) and expose no editor on click, Enter or F2.

## Known follow-ups (not part of this change)

These remain outside the shared inline interaction by the reasons above and are not conditional writes yet:
congregation dialog `PATCH`, activation switches of reminder configs and event hooks, and the duty assignments
panel. They are documented exclusions, not eligible table cells; making them revision-aware is a separate change.
