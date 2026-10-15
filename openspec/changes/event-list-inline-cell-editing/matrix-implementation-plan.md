# Matrix inline editing implementation plan

Base: feat/inline-editing-safe-events (#576).

- Preserve existing MatrixTable navigation and AssignmentModal workflows.
- Expose versioned assignment read model and conditional mutation contract; reject missing If-Match with 428, stale writes with 412, domain conflicts with 409.
- Respect district role checks, cross-district isolation, unavailability and assignment conflict acknowledgments.
- Inline-edit only independently safe fields; preserve confirmation dialogs for destructive changes.
- Test keyboard, touch, stale version, missing permission, conflicts, double submission and >80% coverage.

Status: implemented as a bounded, non-destructive assignment slice; review/CI verification follows each final head. The parent cross-application OpenSpec remains open.


## Implementation checkpoint (2026-10-14)

- [x] Extract the canonical planning-slot strong revision generator and share it with the event API.
- [x] Add `PUT /api/v1/events/{event_id}/assignments/inline` for **non-destructive minister reassignment by leader ID**, guarded by a planning-slot row lock, `If-Match` (428/412), district PLANNER role, existing conflict-check rules (409) and warning acknowledgement.
- [x] Return the new `event_revision`; preserve the existing assignment identity and downgrade a changed CONFIRMED assignment to ASSIGNED for separate reconfirmation.
- [x] Add a strict frontend API adapter and focused backend/API contract regression tests, including missing/stale revision, 403, 409, and attempted implicit deletion.
- [x] Wire a scoped select adapter into both matrix and event overview (desktop/mobile) and expose slot revisions in the matrix read model; preserve existing confirmation dialogs for destructive removal.
- [x] Merge latest #576 and share one composite `PlanningSlot.updated_at + EventInstance.updated_at` revision between event, matrix and assignment endpoints. A slot lock followed by an instance row lock protects the conditional write; instance-only changes return 412.
- [x] Keep removal in the existing explicitly confirmed AssignmentModal. Warning-only 409 conflicts need a confirmation and `confirm_warnings=true`; blocking 409 never proceeds.
- [x] Exercise select activation, conditional saves, warning confirmation/cancellation, blocking conflicts, double submission, scope permissions and event-overview desktop/mobile rendering in focused unit/component tests; the complete frontend E2E suite also passed.
- [ ] Expand dedicated end-to-end matrix flows for touch gestures, simultaneous refresh during sort, multi-scope switch and inaccessible leader choices; maintain as a separate follow-up acceptance task.
- [x] Verified GitHub Actions CI against `main` for the feature branch on 2026-10-14: backend unit 2046 passed/1 skipped, coverage 90%; frontend unit and Playwright E2E succeeded. The PR base must be returned to #576 for the stack. The parent OpenSpec remains open.

The endpoint deliberately cannot delete assignments or write the organisational duty types from the separate `configurable-event-duty-assignments` capability; those require their own business contracts. Legacy assignment endpoints remain supported by the existing dialog pending the full migration.

## Subsequent implementation (2026-10-14)

- Event list and mobile cards now expose a leader-ID selection cell only for active, internal, authorised services in the selected district, excluding invitation-derived rows. The existing modal remains responsible for explicit deletion and free-text assignment.
- A warning-only 409 prompts explicit confirmation; blocking 409 responses remain failures with the draft preserved. The successful inline result updates the row and revision before a best-effort background reload.
- Component tests verify an authorised assignment and that external or destructive cases cannot use this cell.
- The bounded matrix/overview minister assignment slice is implemented, with separate pending cross-application coverage and organisational-duty contracts tracked in parent OpenSpec; those are not part of this PR's non-destructive mutation contract.

## Conflict and navigation contract

- `428`: missing If-Match, before mutation; `412`: stale composite event revision (even an instance-only change); `403`: insufficient district planner role or host-owned invitation; `422`: invalid payload (including null leader ID).
- `409`: a BLOCK conflict (unavailability, double-booking or travel-time conflict) is not overrideable; a WARN conflict is retried only after the user explicitly acknowledges it. Cancelled slots and multiple contradictory assignment rows also return 409 without mutation.
- Single-active-cell coordination is shared with #576. Focus traversal is scoped to the visible matrix table; invalid drafts remain in place until corrected or cancelled with Escape. Existing explicit removal dialogs remain the sole destructive path.
- A separate persistent version column can replace this opaque timestamp-based composite validator in a future schema migration; this slice reuses the current backend contract to avoid dual revision domains.

## Review refinements (2026-10-15)

- Invitation copies never expose inline assignment editing, even if an older or inconsistent read model reports them as editable. Host-owned assignments remain protected independently by the server.
- Matrix and event overview use the same `useInlineAssignmentSave` composable and application confirmation host. Only explicit WARN-only conflicts may be acknowledged; BLOCK, unknown severities and malformed/non-warning responses never trigger a retry. A confirmed retry keeps the original revision and is attempted once.
- Missing If-Match returns 428 before any repository access or lock. Valid requests always lock the slot before reading the instance.
- The canonical `slot_revision` name is used directly. The `none` instance marker is opaque: inserting the first EventInstance invalidates a previous slot-only validator.
- Regression tests cover inconsistent invitation editability, warning cancellation, blocking/mixed/unknown conflicts, retry failure and instance insertion. Final merge readiness requires CI evidence at the new branch head.
