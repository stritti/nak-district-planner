## 1. Domain, API and persistence

- [x] 1.1 Add manual POST create, typed request validation, and initial PLANNED state.
- [x] 1.2 Add DELETE only for never-released drafts and lock the record against concurrent release.
- [x] 1.3 Persist first-release marker and migrate existing confirmed records.
- [x] 1.4 Disallow unpublication and reopening of published cancellations.
- [x] 1.5 Prevent published hard deletes from sync and invitation paths.
- [x] 1.6 Preserve generated-draft deletion suppression across recurring auto-generation using a tenant-scoped suppression ledger.

## 2. Frontend and exports

- [x] 2.1 Add creation dialog and guarded draft-deletion action with confirmation.
- [x] 2.2 Keep ICS cancelled UID and XLSX `Abgesagt` behavior.

## 3. Verification

- [x] 3.1 Add targeted backend lifecycle validation and repository unit tests.
- [x] 3.2 Add frontend API and interaction tests.
- [ ] 3.3 Run backend tests, frontend coverage >80%, full CI and OpenSpec validation.
- [x] 3.4 Add explicit external `HARD_DELETE` after release regression tests.
