## 1. Field Classification

- [x] 1.1 Define SyncFieldAuthority enum
- [x] 1.2 Implement field-to-authority mapping
- [x] 1.3 Route fields by authority
- [x] 1.4 Default unclassified fields to STRUCTURAL
- [ ] 1.5 Diff fields before conflict transition
- [ ] 1.6 Merge non-overlapping SOFT changes while DIRTY_INTERNAL

## 2. Deviation Detection & Resolution

- [x] 2.1 Detect start-time deviation
- [x] 2.2 Store external actual start/end on EventInstance
- [x] 2.3 Set deviation_flag for start deviation
- [x] 2.4 Expose deviation resolution endpoint
- [ ] 2.5 Detect end-time/duration-only deviation
- [ ] 2.6 Push resolved deviation to writable external provider
- [ ] 2.7 Persist outbound acknowledgement before returning CLEAN
- [ ] 2.8 Preserve state-machine semantics when resolving from CONFLICT
- [ ] 2.9 Return non-success/explicit idempotent result when no deviation can be resolved

## 3. Symmetric Deletion

- [x] 3.1 Handle explicit external cancellation
- [x] 3.2 Push internal deletion to writable CalendarConnector
- [x] 3.3 Prevent self-originated deletion loops
- [ ] 3.4 Parse timestamp-less provider tombstones
- [ ] 3.5 Reconcile missing resources from authoritative snapshots
- [ ] 3.6 Persist delete policy per CalendarIntegration
- [ ] 3.7 Make repeated acknowledged cancellation a write-free no-op
- [ ] 3.8 Preserve/update tombstone audit metadata for HARD_DELETE

## 4. Partial Failure & Connector Contract

- [ ] 4.1 Normalize transport/credential/provider failures to CalendarConnectorError
- [ ] 4.2 Add failed counter separate from skipped
- [ ] 4.3 Expose failed count through HTTP and background jobs
- [ ] 4.4 Preserve integration-level partial failure summary

## 5. Auto-match Integrity

- [ ] 5.1 Reuse matched PlanningSlot when EventInstance is missing

## 6. Tests

- [x] 6.1 Unit tests for field classification baseline
- [x] 6.2 Unit tests for start deviation baseline
- [x] 6.3 Unit tests for explicit deletion propagation baseline
- [x] 6.4 Unit tests for deletion loop prevention baseline
- [ ] 6.5 SOFT-only external change during DIRTY_INTERNAL
- [ ] 6.6 end-time-only deviation
- [ ] 6.7 successful and failed outbound deviation resolution
- [ ] 6.8 Google tombstone without timestamps
- [ ] 6.9 Microsoft/CalDAV missing-resource reconciliation
- [ ] 6.10 incomplete snapshot must not delete
- [ ] 6.11 two integrations with different delete policies
- [ ] 6.12 connector timeout/credential error isolation and failed reporting
- [ ] 6.13 repeated cancellation causes no additional writes
- [ ] 6.14 matched slot without instance creates no duplicate slot
