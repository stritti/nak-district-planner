# Dependent event changes implementation plan

Base: `feat/inline-edit-matrix` (#577), stacked on #576.

## Implemented scope

- Preserve existing full-editor flows for event workflow fields. The direct inline-cell adapter continues to allow independently safe scalar edits only; dependent date/time/congregation fields require the separate full-editor workflow.
- Require `If-Match` for every event PATCH and for `POST /api/v1/events/{id}/change-impact`. The strong event revision covers both PlanningSlot and EventInstance timestamps; missing revision is 428, outdated revision 412.
- Obtain row locks in one consistent order: PlanningSlot `get_for_update` first, EventInstance locked read second; for dependent changes, acquire per-leader advisory transaction locks in sorted UUID order before validation. The mutation revalidates conflicts before either event model is written.
- Preview returns conflicts bound to the matching event snapshot. The user can acknowledge WARN conflicts and the final PATCH revalidates against the same revision. BLOCK conflicts reject with 409. 403 represents missing scope/ownership; 400/422 represent invalid input or foreign references.
- Preserve explicit confirmation for event cancellation and assignment removal; never clear dependent assignments implicitly. A failed preview/write retains the edit form draft.
- Use existing conflict checker for overlapping assignments, travel-time rules and leader unavailability, including the proposed congregation and schedule.
- Refresh the persisted event revision after edits that also change service assignments, preserving the safe optimistic-concurrency model.

## Merge-readiness acceptance

- [x] Backend unit tests cover 428/412, impact preview, no-write BLOCK rejection, explicit WARN acknowledgement, role isolation and deterministic advisory lock ordering.
- [x] Frontend API/component tests cover preview revision forwarding, blocked change, acknowledged warnings and ordinary edit workflow.
- [ ] Reverify the updated stacked head in GitHub Actions CI, including >=80% overall and required router coverage, all frontend tests, E2E and OpenSpec/docs validations.
- [ ] Close review threads only after checking the actual tests and code paths; do not claim parent OpenSpec complete.

## Deferred domain changes

- Editing category from a service to another type while assignments exist needs a dedicated explicit migration/removal workflow; never silently discard assignments.
- Full inline calendar-based date/time editing, general cross-application table migration and configurable organisational duties belong in independently reviewable later slices, with their own specs and tests.
- A persistent integer version on PlanningSlot/EventInstance could replace timestamp-based validators after an explicit schema migration; this PR deliberately reuses the canonical #576/#577 representation.
