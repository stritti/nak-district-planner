# Matrix inline editing implementation plan

Base: feat/inline-editing-safe-events (#576).

- Preserve existing MatrixTable navigation and AssignmentModal workflows.
- Expose versioned assignment read model and conditional mutation contract; reject missing If-Match with 428, stale writes with 412, domain conflicts with 409.
- Respect district role checks, cross-district isolation, unavailability and assignment conflict acknowledgments.
- Inline-edit only independently safe fields; preserve confirmation dialogs for destructive changes.
- Test keyboard, touch, stale version, missing permission, conflicts, double submission and >80% coverage.

Status: planned, implementation outstanding.


## Implementation checkpoint (2026-10-14)

- [x] Extract the canonical planning-slot strong revision generator and share it with the event API.
- [x] Add `PUT /api/v1/events/{event_id}/assignments/inline` for **non-destructive minister reassignment by leader ID**, guarded by a planning-slot row lock, `If-Match` (428/412), district PLANNER role, existing conflict-check rules (409) and warning acknowledgement.
- [x] Return the new `event_revision`; preserve the existing assignment identity and downgrade a changed CONFIRMED assignment to ASSIGNED for separate reconfirmation.
- [x] Add a strict frontend API adapter and focused backend/API contract regression tests, including missing/stale revision, 403, 409, and attempted implicit deletion.
- [x] Wire a scoped select adapter into both matrix and event overview (desktop/mobile) and expose slot revisions in the matrix read model; preserve existing confirmation dialogs for destructive removal.
- [ ] After stacking onto the latest #576, use the same composite PlanningSlot/EventInstance validator across matrix and event APIs; reject stale instance-only updates too.
- [ ] Preserve confirmation before clearing an existing assignment and expose warning acknowledgement via the existing modal flow.
- [ ] Prove end-to-end behavior with component/E2E tests, including sorting, changes while editing, foreign district, 409 warning confirmation, cancellation, double submit and mobile.
- [ ] Verify CI on the updated stacked head and >80% coverage; do not mark the parent OpenSpec as complete.

The endpoint deliberately cannot delete assignments or write the organisational duty types from the separate `configurable-event-duty-assignments` capability; those require their own business contracts. Legacy assignment endpoints remain supported by the existing dialog pending the full migration.

## Subsequent implementation (2026-10-14)

- Event list and mobile cards now expose a leader-ID selection cell only for active, internal, authorised services in the selected district, excluding invitation-derived rows. The existing modal remains responsible for explicit deletion and free-text assignment.
- A warning-only 409 prompts explicit confirmation; blocking 409 responses remain failures with the draft preserved. The successful inline result updates the row and revision before a best-effort background reload.
- Component tests verify an authorised assignment and that external or destructive cases cannot use this cell.
- The branch is still a Draft stacked PR: synchronize with the final #576 base, verify CI and coverage, test keyboard/mobile, and address optional organisational duties in their own domain contract before claiming full OpenSpec acceptance.
