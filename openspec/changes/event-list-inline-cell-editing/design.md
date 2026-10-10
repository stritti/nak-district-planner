## Context

The event list is backed by `GET /api/v1/events`, with individual event edits through `PATCH /api/v1/events/{id}`. Responsible-person assignments use `/api/v1/events/{event_id}/assignments` and share the matrix's conflict policy. PlanningSlot stores canonical planning data; EventInstance stores observed/externally synchronised instance details.

## Decisions

### Read mode first

All cells render as short text by default with no persistent input borders or action buttons. Truncate long values visually with accessible full-value reveal, preserve column headings and important status indicators, and keep empty values distinguishable from loading/errors. Focus/click on an editable cell opens a clearly focused input/select/date/time picker; read-only cells never imply editability. Only one cell is in edit mode at a time. Keyboard activation is Enter/F2, then Enter commits (except multiline, if introduced), Escape cancels, Tab commits and advances according to row order, and Shift+Tab commits and moves backwards. Clicking elsewhere attempts validation and save; failure keeps the draft and error visible without silently discarding data. Mobile/touch activation shows an appropriate popover/editor without hover dependence.

### Field schema and safe updates

Use a frontend field-definition registry of explicitly editable fields, with per-field display formatter, control, converter, validator and API adapter. Match the actual fields and restrictions returned by the current events API. Exclude server-generated identifiers, origin, audit/sync metadata and fields not editable by the logged-in role. Updates should be scoped to a single field or the smallest required atomic dependent set; preserve untouched values. For the responsible-person column, route changes through the existing assignments endpoint, including 409 conflict acknowledgement, and never through generic event PATCH. Additional organisational duty roles defined in `configurable-event-duty-assignments` use their own scoped assignment endpoints and MUST NOT be conflated with the liturgical leader. Changing a slot's category or congregation SHALL trigger the duty-validity and scope checks of that change; existing duty assignments remain stored and any newly ineligible duties are flagged for review, not silently deleted. Changing date/time with an existing minister assignment must likewise re-evaluate service-end-date eligibility and surface required review without silently removing historical references.

### Network state and consistency

Maintain the previously persisted cell value and a separate draft until a successful response. Indicate saving in the active cell; disable reentrant submissions. On 4xx validation or 409 conflict keep editor open with submitted value and message; on transport failures keep it retryable. Do not overwrite another editor's newer data: every inline write MUST use an authoritative resource revision in an `If-Match` precondition (opaque strong ETag, or an equivalent explicit version contract where a legacy endpoint already exposes one). For endpoints lacking conditional writes, add backend revision support before making the corresponding column editable; never fall back to blind PATCH/PUT. Missing preconditions on newly added mutation contracts return 428 and stale versions return 412, retaining the draft and offering a reload/compare flow. Existing domain conflicts and warning acknowledgements remain 409. Responses SHALL provide a new revision for subsequent edits. Re-fetch row data after successful mutations and reconcile active filters/sorting without losing selection. Restore original display on Escape only before commit. Never silently accept a failed update.

### Permissions and accessibility

Show edit affordances only where the effective `PLANNER` role permits writes in the event scope, while backend checks remain authoritative. Use semantic table cells and accessible labels including row identification and column name, visible keyboard focus, screen-reader announcements of save/error, and minimum touch targets. Confirm destructive or cancellation actions per existing frontend-ux policy rather than treating them as ordinary inline changes.

## Risks

- Lost updates: conditional writes and conflict recovery required.
- Changing sort/filter values moves rows: reconcile against canonical server result and retain keyboard focus as possible.
- External calendar authority: do not permit editing protected fields.
- Sparse responsive table: avoid always-visible controls and preserve accessible full values.

## Shared table-editing architecture

Implement a reusable, framework-idiomatic Vue table-cell editing primitive/composable and a declarative field adapter contract, rather than copying bespoke editing state and keyboard handling into each screen. The shared contract defines display formatting, editor type, editability predicate (role, resource status and field ownership), parse/validate, save adapter, conflict recovery, focus/navigation and accessibility. Each table retains its own domain API and business rules; the shared layer MUST NOT issue unrestricted generic mutations.

Inventory all existing table/list/matrix surfaces before implementation. Classify each column as editable scalar/reference, read-only/derived, link/navigation, or action/workflow. Capture existing permissions and endpoints per surface and use that mapping to phase implementation. Tables without editable columns SHALL still adopt consistent dense read-only rendering and accessible focus semantics, without introducing fake editors. Bulk actions, approvals, deletes and other destructive or multi-step workflows remain explicit and confirmed. Do not interpret a click on a link or selection checkbox as permission to edit.

A shared contract governs click/touch/Enter/F2 activation, Escape cancel, Enter/Tab/Shift+Tab save, blur handling, per-cell saving and recoverable error status. If the current cell cannot save, focus must not silently advance and the draft must survive. Reconcile sort/filter/page refresh after saves, including editors in virtualised or horizontally scrolling tables. Never update a row the user cannot edit, and always enforce tenant/RBAC rules server-side.

Editors that require destructive removal, confirmation, or a business workflow (including clearing a leader assignment where that deletes the record) SHALL preserve the existing confirmation/modal flow instead of treating it as an ordinary blur-triggered save. Moving focus onto actions, links or rows that reorder after a commit SHALL not trigger a second submission.

## Rollout and acceptance

Do not declare the feature complete after migrating the event overview. Require an explicit inventory with all tabular screens and disposition, shared component tests, and screen-specific integration regressions for every eligible table. If a table is intentionally excluded, record the precise non-editable/domain reason in the inventory and verify it still uses the consistent read-only display. Maintain >80% coverage, including keyboard, async error, concurrency and permissions paths.
