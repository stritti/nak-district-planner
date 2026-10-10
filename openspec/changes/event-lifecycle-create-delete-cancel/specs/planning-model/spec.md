## MODIFIED Requirements

### Requirement: Retention cleanup
The beat task `cleanup_old_events` SHALL delete only never-released planning slots whose `planning_date` is older than 24 months on the first day of each month and SHALL record one bulk-delete audit entry. Previously released events (including cancelled events) SHALL NOT be permanently removed by retention. Retention SHALL use the relationship-aware PlanningSlot repository deletion to clear invitation links, delete unreleased target copies, and retain released target copies as cancellations.

#### Scenario: Old unreleased slots removed
- **WHEN** the cleanup runs
- **THEN** never-released slots older than the cutoff and their dependent rows are removed and an audit row with reason `retention` exists

#### Scenario: Retention of an invited draft
- **WHEN** a never-released invitation source passes the retention cutoff
- **THEN** its invitations and unpublished target copies are removed and any released target copy survives as `CANCELLED`

#### Scenario: Old released slots retained
- **WHEN** the cleanup runs and older released or cancelled events exist
- **THEN** the released event identities and their dependent occurrences remain intact

### Requirement: Events API over planning slots
`GET /api/v1/events` SHALL list slots of a district for `VIEWER` (superadmins MAY omit `district_id`) with filters for congregation, group, district level, status, approval status, `is_service`, time range (default one year back to two years ahead) and pagination. `PATCH /api/v1/events/{id}`, `POST /api/v1/events` and `DELETE /api/v1/events/{id}` SHALL require `PLANNER` in the relevant district. On creation, a new `PlanningSlot` and `EventInstance` SHALL be saved atomically with status `ACTIVE` and approval `PLANNED`. Creation and updates SHALL reject foreign-district congregations and invalid time ranges. A manually deleted event SHALL be absent from subsequent event listings.

#### Scenario: New draft event
- **WHEN** a planner creates a valid event with start, end and title
- **THEN** the server returns 201, saves a `PLANNED` slot and INTERNAL-sourced instance, and returns its stable ID

#### Scenario: Invalid event
- **WHEN** a planner provides an end earlier than or equal to start, an unrecognized congregation or an invalid distribution
- **THEN** the server rejects the request without saving an event

#### Scenario: Congregation from another district
- **WHEN** a planner moves an event to a congregation of another district
- **THEN** the API responds with 400

## ADDED Requirements

### Requirement: Irreversible event publication boundary
The first release of a slot SHALL be recorded in `released_at` and SHALL never be forgotten. Existing `CONFIRMED` slots SHALL be treated as previously released. A slot which was ever released SHALL NOT be hard-deleted or reverted to `PLANNED`; instead it MAY be marked `CANCELLED` and SHALL retain its stable ID. Repository-level delete and update checks SHALL lock and refresh persisted rows so a concurrent release cannot be removed or downgraded by stale writes. Concurrent deletion of invitation sources and linked target slots SHALL acquire the district transaction lock before any row or invitation locks. The monthly retention cleanup SHALL preserve all previously released events, including cancellations. Deleting an unreleased source or target event SHALL also remove linked invitations; unreleased invitation target copies SHALL be deleted, while released target copies SHALL survive with `CANCELLED` status. A published cancellation SHALL NOT be reopened to `ACTIVE`. Editing or bulk-updating a draft that has been concurrently deleted SHALL return HTTP 409 and SHALL NOT re-create the removed event ID. Removal of a linked invitation SHALL lock the target state before choosing between deleting an unreleased copy and cancelling a released copy.

#### Scenario: Draft deleted
- **WHEN** a planner deletes an event that has never been confirmed
- **THEN** the slot and its dependent occurrences are deleted; generated slots first persist their generation key in a separate suppression ledger; the endpoint returns 204

#### Scenario: Released event deletion blocked
- **WHEN** deletion of a current or formerly confirmed event is requested
- **THEN** the endpoint returns 409 and the event remains available for cancellation exports

#### Scenario: Attempt to withdraw publication
- **WHEN** a single or bulk approval request attempts to return a released event to `PLANNED`
- **THEN** it returns 409 without applying the downgrade

#### Scenario: Concurrent source and linked target deletion
- **WHEN** planners delete an invitation source and target simultaneously
- **THEN** both deletions acquire the same district lock before individual slot and invitation locks, avoiding deadlocks

#### Scenario: Concurrent deletion during event update
- **WHEN** a PATCH or monthly bulk approval update loaded a draft that another transaction subsequently deleted
- **THEN** the update returns HTTP 409, never recreates the event, and publishes no partially applied monthly result

#### Scenario: Concurrent release during invitation removal
- **WHEN** an invitation target becomes released while the invitation removal starts
- **THEN** the locked latest target is cancelled rather than deleted and the invitation is removed without HTTP 500

#### Scenario: Invitation source deletion
- **WHEN** a planner deletes an unreleased invitation source event
- **THEN** its invitations and unreleased target copies disappear, but released target copies retain their identity and become `CANCELLED`

#### Scenario: Invitation target deletion
- **WHEN** a planner deletes an unreleased invited target event
- **THEN** the corresponding invitation is removed without deleting its source event

#### Scenario: Concurrent update after release
- **WHEN** an outdated draft update races with another request confirming the same slot
- **THEN** the persisted release is protected under a row lock, the stale downgrade is rejected, and PATCH returns HTTP 409 instead of 500

#### Scenario: Concurrent monthly publication update
- **WHEN** a bulk approval request reads an unpublished slot and another transaction publishes or cancels it before the repository save
- **THEN** the request receives HTTP 409 rather than 500 and the transaction does not publish a partial monthly result

#### Scenario: Retention of released cancellations
- **WHEN** the monthly retention job runs and an event was previously released
- **THEN** that event remains available even when its planned date is older than the retention cutoff

#### Scenario: Provider hard delete after release
- **WHEN** a linked provider removes a released event configured for `HARD_DELETE`
- **THEN** the slot survives with `CANCELLED` status and the original event identity

#### Scenario: Generated draft deleted
- **WHEN** a planner deletes a generated draft that has a generation key
- **THEN** it is deleted from the events table and exports, its generator key is kept in a district-scoped deletion ledger, and it is not regenerated by the next nightly generation run

### Requirement: Persist manual deletion of generated draft occurrences
When an unpublished generated event is deleted, a tenant-scoped suppression marker SHALL retain the generated occurrence identity, without retaining the event or its instance. Both rolling draft service generation and recurring PlanningSeries generation SHALL skip suppressed occurrences. Legacy series slots without a generation key SHALL be suppressed using their series ID and UTC planning date. A series slot whose generation key was explicitly detached on reassignment SHALL NOT create such a suppression marker on deletion. Both the scheduled series generator and the explicit series slot generation service SHALL handle concurrent uniqueness conflicts by skipping the already inserted occurrence and preserving the rest of the transaction. Both generators SHALL acquire the same district-scoped transaction lock as deletion before querying or inserting occurrences, in a deterministic district order, and SHALL read existing generation keys before deletion markers so a committed deletion cannot be regenerated. Legacy series existence checks SHALL ignore detached occurrences. A suppression marker SHALL NOT block another district's independent occurrence.

#### Scenario: Deleted generated Gottesdienst
- **WHEN** a planner deletes an autogenerated unreleased Gottesdienst and the draft generator runs again
- **THEN** the removed slot is not recreated

#### Scenario: Concurrent series generation
- **WHEN** two schedulers attempt to insert the same recurring occurrence
- **THEN** only one slot is stored and the second attempt is skipped without an orphan instance or aborted batch

#### Scenario: Concurrent explicit series generation
- **WHEN** two manual or background requests generate the same planning-series occurrence concurrently
- **THEN** the second insert is counted as skipped without an uncaught unique constraint exception, and other slots from the run remain created

#### Scenario: Concurrent deletion between generator reads
- **WHEN** deletion of a series occurrence commits between an existing-slot read and a tombstone read
- **THEN** the generator observes its deletion marker and does not regenerate the occurrence

#### Scenario: Detached legacy series occurrence
- **WHEN** an occurrence is reassigned to another congregation or category
- **THEN** neither generator treats its detached slot as the original occurrence

#### Scenario: Reassigned series occurrence deleted
- **WHEN** a detached series draft is deleted after reassignment to a different congregation or category
- **THEN** the original series occurrence remains eligible for generation

#### Scenario: Deleted recurring series occurrence
- **WHEN** a planner removes one unreleased series occurrence and a scheduler regenerates the same series
- **THEN** that occurrence stays deleted while other dates in the series may still be generated
