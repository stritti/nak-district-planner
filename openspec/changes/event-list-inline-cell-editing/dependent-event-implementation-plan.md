# Dependent event changes implementation plan

Base: `feat/inline-edit-matrix` (#577), stacked on #576.

## Implemented scope

- Preserve existing full-editor flows for event workflow fields. The direct inline-cell adapter continues to allow independently safe scalar edits only; dependent date/time/congregation fields require the separate full-editor workflow.
- Require `If-Match` for every event PATCH and for `POST /api/v1/events/{id}/change-impact`. The strong event revision covers both PlanningSlot and EventInstance timestamps; missing revision is 428, outdated revision 412.
- Obtain row locks in one consistent order: PlanningSlot `get_for_update` first, EventInstance locked read second; for dependent changes, acquire per-leader advisory transaction locks in sorted UUID order before validation. Legacy assignment create/update/delete writers acquire the same PlanningSlot lock before loading or mutating assignment rows. The mutation revalidates conflicts before either event model is written.
- Preview returns conflicts bound to the matching event snapshot. The user can acknowledge WARN conflicts and the final PATCH revalidates against the same revision. BLOCK conflicts reject with 409. 403 represents missing scope/ownership; 400/422 represent invalid input or foreign references.
- Preserve explicit confirmation for event cancellation and assignment removal; never clear dependent assignments implicitly. A failed preview/write retains the edit form draft.
- Use existing conflict checker for overlapping assignments, travel-time rules and leader unavailability, including the proposed congregation and schedule.
- Refresh the persisted event revision after edits that also change service assignments, preserving the safe optimistic-concurrency model.

## Merge-readiness acceptance

- [x] Backend unit tests cover 428/412, impact preview, no-write BLOCK rejection, explicit WARN acknowledgement, role isolation and deterministic advisory lock ordering.
- [x] Frontend API/component tests cover preview revision forwarding, blocked change, acknowledged warnings and ordinary edit workflow.
- [x] Verified the implementation on GitHub Actions: backend 2,063 passing unit tests (+246 passing integration tests), 90% overall code coverage (minimum >80%), frontend unit and E2E passed; lint, security, migrations and documentation gates checked on the stacked implementation.
- [x] Review feedback incorporated: stable multi-entity lock order, snapshot-guarded impact preview, 409/412/422 separation and a small dependent-change slice; the original parent OpenSpec stays open for further table integrations.

## Additional concurrency regression coverage

- [x] Reproduced legacy assignment race with three initially failing tests (`create`, `update`, `delete`); the writer lock fix makes all three pass.
- [x] Aligned existing writer unit fixtures with the transactional PlanningSlot lock; newly restricted paths do not expose foreign assignment existence before authorisation.
- [x] Confirmed consistent `If-Match` semantics in the frontend: status-only and dependent full-editor PATCHes both require the loaded revision.

## Deferred domain changes

- Editing category from a service to another type while assignments exist needs a dedicated explicit migration/removal workflow; never silently discard assignments.
- Full inline calendar-based date/time editing, general cross-application table migration and configurable organisational duties belong in independently reviewable later slices, with their own specs and tests.
- A persistent integer version on PlanningSlot/EventInstance could replace timestamp-based validators after an explicit schema migration; this PR deliberately reuses the canonical #576/#577 representation.

## Review refinements (2026-10-15)

- The final PATCH handles a newly arriving WARN-only 409 just like the preview: it asks for explicit acknowledgement and retries once, retaining the exact payload and original If-Match revision. Cancelling leaves the full-editor draft open. BLOCK, unknown severities, stale revisions and a failed retry remain failures; conflict messages are readable in the form.
- The dependency trigger explicitly checks requested congregation/start/end fields against the effective persisted values. No-op schedule/location writes do not repeat conflict validation. Category migration with assignments remains deliberately outside this trigger and requires the deferred explicit migration/removal workflow.
- Missing If-Match returns 428 before repository access; every valid PATCH always takes the PlanningSlot lock, followed by the EventInstance lock.
- Preview intentionally accepts write-lock serialization for a consistent snapshot at the current isolation level. Its transaction ends after the response; the final PATCH uses a separate transaction and must revalidate.
- The strict `EventUpdate` request retains `confirm_warnings` as a full-editor workflow option (review alternative a), described explicitly in the schema. It is never copied into persisted event fields and only affects dependent validation. A new dependent-only route/schema would break existing full-editor clients without improving this slice's safety; scalar inline requests still forbid workflow flags.
- Regression tests cover warnings arriving after clean/acknowledged previews, cancellation, mixed/unknown/BLOCK conflicts, stale revisions, bounded retry failure, missing-header no-read behavior and no-op/instance-aware dependency detection.
