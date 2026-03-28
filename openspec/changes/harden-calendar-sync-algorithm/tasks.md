## 1. Sync Metadata

- [ ] 1.1 Add sync_state field to EventInstance
- [ ] 1.2 Add last_synced_hash field
- [ ] 1.3 Add last_internal_modified_at field
- [ ] 1.4 Add last_external_modified_at field

## 2. External Mapping

- [ ] 2.1 Create ExternalEventLink table
- [ ] 2.2 Persist external revision markers
- [ ] 2.3 Link ExternalEventLink to EventInstance

## 3. State Machine Implementation

- [ ] 3.1 Implement sync state transition logic
- [ ] 3.2 Implement structural vs soft field diffing
- [ ] 3.3 Implement conflict state handling

## 4. Idempotency and Loop Prevention

- [ ] 4.1 Implement payload hash comparison
- [ ] 4.2 Implement outbound revision tracking
- [ ] 4.3 Implement inbound revision guard

## 5. Delete Handling

- [ ] 5.1 Implement MARK_CANCELLED behavior
- [ ] 5.2 Implement HARD_DELETE behavior

## 6. Integration Tests

- [ ] 6.1 Test duplicate webhook handling
- [ ] 6.2 Test concurrent internal/external modification
- [ ] 6.3 Test delete behavior modes
