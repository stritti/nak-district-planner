## 1. Sync Metadata

- [x] 1.1 Add sync_state field to EventInstance
- [x] 1.2 Persist last_synced_hash on ExternalEventLink
- [x] 1.3 Add last_internal_modified_at field
- [x] 1.4 Add last_external_modified_at field

## 2. External Mapping

- [x] 2.1 Create ExternalEventLink table
- [x] 2.2 Persist external revision markers
- [x] 2.3 Link ExternalEventLink to EventInstance
- [x] 2.4 Add repository support to list active links by integration/reconciliation scope
- [x] 2.5 Define durable tombstone lifecycle and audit timestamps
- [x] 2.6 Add explicit ACTIVE/SYNC_TOMBSTONE state (with deletion origin/reason); never infer tombstone intent from event_instance_id IS NULL
- [x] 2.7 Audit non-sync EventInstance deletion flows to remove links or deliberately enter the sync-deletion transition

## 3. Field-aware State Machine

- [x] 3.1 Implement base sync state transition logic
- [x] 3.2 Implement structural vs soft field classification
- [x] 3.3 Persist CONFLICT state
- [x] 3.4 Compute changed fields before conflict transition
- [x] 3.5 Merge non-overlapping SOFT changes while DIRTY_INTERNAL
- [x] 3.6 Route deviation/conflict resolution through state-machine functions
- [x] 3.7 Expose CONFLICT state and resolution endpoint to PLANNER

## 4. Idempotency and Loop Prevention

- [x] 4.1 Implement payload hash comparison
- [x] 4.2 Implement outbound revision tracking
- [x] 4.3 Implement inbound revision guard
- [x] 4.4 Skip already acknowledged cancellation tombstones without DB writes
- [ ] 4.5 Verify update and delete echo suppression for every writable provider
- [x] 4.6 Before outbound delete, compare provider state with last acknowledged hash/revision and route concurrent remote edits through field-aware conflict handling

## 5. Provider Deletion Reconciliation

- [x] 5.1 Implement MARK_CANCELLED behavior
- [x] 5.2 Implement HARD_DELETE behavior
- [x] 5.3 Persist delete_behavior per CalendarIntegration and migrate existing integrations
- [x] 5.4 Parse Google cancelled tombstones before validating start/end timestamps
- [x] 5.5 Define connector metadata indicating authoritative/full reconciliation scope
- [x] 5.6 Reconcile active links missing from authoritative provider snapshots
- [x] 5.7 Never infer deletion from partial, failed, incremental, or narrowed responses
- [x] 5.8 Update retained tombstone audit timestamp in HARD_DELETE flow

## 6. Bidirectional Deviation Resolution

- [x] 6.1 Detect start-time deviation
- [x] 6.2 Detect end-time/duration-only deviation
- [x] 6.3 Add connector update operation for corrected times
- [x] 6.4 Push resolved deviations to writable external providers
- [x] 6.5 Persist outbound revision/hash and return to CLEAN only after acknowledgement
- [x] 6.6 Return meaningful API status when no resolvable deviation exists or outbound sync fails
- [x] 6.7 Derive resolved end time from the authoritative planned-duration rule, never from the deviating actual duration

## 7. Partial Failure Contract

- [x] 7.1 Isolate CalendarConnectorError per event
- [x] 7.2 Translate transport, credential, HTTP, and provider concurrency failures to CalendarConnectorError
- [x] 7.3 Add SyncResult.failed distinct from skipped
- [x] 7.4 Expose failed count in HTTP and background-job results
- [x] 7.5 Preserve bounded last_sync_error summary for partial failures

## 8. Auto-match Integrity

- [x] 8.1 Attach/create EventInstance on an existing matched PlanningSlot without creating a duplicate slot

## 9. Tests

- [x] 9.1 Test duplicate webhook handling
- [x] 9.2 Test concurrent internal/external modification baseline
- [x] 9.3 Test delete behavior modes baseline
- [x] 9.4 Test Google timestamp-less cancellation tombstone
- [x] 9.5 Test missing-resource reconciliation for authoritative Microsoft/CalDAV snapshots
- [x] 9.6 Test no false deletion on incomplete/failed/narrowed fetch
- [x] 9.7 Test SOFT-only external change while DIRTY_INTERNAL
- [x] 9.8 Test end-time-only deviation and outbound resolution
- [x] 9.9 Test per-integration delete policies in the same process
- [x] 9.10 Test transport and credential failures remain isolated and observable
- [x] 9.11 Test repeated cancellation produces no recurring writes
- [x] 9.12 Test auto-match without EventInstance does not duplicate PlanningSlot
- [x] 9.13 Test non-sync EventInstance deletion cannot create a synchronization tombstone
- [x] 9.14 Test only explicit sync HARD_DELETE transitions a link to SYNC_TOMBSTONE
- [x] 9.15 Test local delete versus concurrent provider edit preserves provider event and enters conflict handling
- [x] 9.16 Test duration deviation resolution restores planned duration
- [x] 9.17 Test repeated/stale deviation resolution reports explicit no-op/non-success
