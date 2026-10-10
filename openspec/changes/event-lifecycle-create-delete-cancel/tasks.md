## 1. Domain, API and persistence

- [x] 1.1 Add manual POST create, typed request validation, and initial PLANNED state.
- [x] 1.2 Add DELETE only for never-released drafts and lock the record against concurrent release.
- [x] 1.3 Persist first-release marker and migrate existing confirmed records.
- [x] 1.4 Disallow unpublication and reopening of published cancellations.
- [x] 1.5 Prevent published hard deletes from sync and invitation paths.
- [x] 1.6 Preserve deleted drafts across eight-week service and PlanningSeries auto-generation, including legacy series slots, using a tenant-scoped suppression ledger.

## 2. Frontend and exports

- [x] 2.1 Add creation dialog and guarded draft-deletion action with confirmation.
- [x] 2.2 Keep ICS cancelled UID and XLSX `Abgesagt` behavior.

## 3. Verification

- [x] 3.1 Add targeted backend lifecycle validation and repository unit tests.
- [x] 3.2 Add frontend API and interaction tests.
- [ ] 3.3 Run backend tests, frontend coverage >80%, full CI and OpenSpec validation.
- [x] 3.4 Add explicit external `HARD_DELETE` after release regression tests.

## 4. Codex review follow-up

- [x] 4.1 Clean up source/target invitations and preserve released target cancellations.
- [x] 4.2 Use conflict-safe series generation and cover competing inserts.
- [x] 4.3 Preserve released events during monthly retention cleanup.
- [x] 4.4 Track deliberately detached generation keys separately from legacy occurrences.
- [x] 4.5 Lock and refresh updates before checking irreversible publication.
- [ ] 4.6 Re-run CI, coverage, migration and strict OpenSpec validation after the corrections.

## 5. Second Codex review follow-up

- [x] 5.1 Map release races during PATCH and bulk approval writes to HTTP 409.
- [x] 5.2 Use conflict-safe insertion in PlanningSeriesSlotGenerationService as well as PlanningSeriesGenerator.
- [x] 5.3 Add regression tests for stale updates, monthly release races and concurrent/manual series generation.
- [ ] 5.4 Verify changed branch with full CI and active OpenSpec change validation.

## 6. Third Codex review follow-up

- [x] 6.1 Require persisted row on PATCH and bulk update; reject concurrent deletes without recreation.
- [x] 6.2 Lock and refresh invitation targets before deleting or cancelling.
- [x] 6.3 Route retention cleanup through relationship-safe repository deletion and test released copies.
- [x] 6.4 Reset the creation form's congregation after save and across district switches.
- [ ] 6.5 Verify full CI, coverage and strict active OpenSpec change validation.
