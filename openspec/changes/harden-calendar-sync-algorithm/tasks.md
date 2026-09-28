## 1. Sync Metadata

- [x] 1.1 Add sync_state field to EventInstance *(`SyncState`-Enum + Feld in `domain/models/event_instance.py`, Sync setzt CLEAN/DIRTY_EXTERNAL)*
- [x] 1.2 Add last_synced_hash field *(in `ExternalEventLink.last_synced_hash` persistiert statt direkt auf EventInstance — siehe 2.1)*
- [x] 1.3 Add last_internal_modified_at field
- [x] 1.4 Add last_external_modified_at field

## 2. External Mapping

- [x] 2.1 Create ExternalEventLink table *(`domain/models/external_event_link.py` + ORM + Repository)*
- [x] 2.2 Persist external revision markers *(`revision_marker`-Feld in ExternalEventLink)*
- [x] 2.3 Link ExternalEventLink to EventInstance *(`event_instance_id`-FK)*

## 3. State Machine Implementation

- [ ] 3.1 Implement sync state transition logic *(CLEAN/DIRTY_EXTERNAL-Übergänge im Sync vorhanden; formale State-Machine mit DIRTY_INTERNAL-/Konflikt-Zuständen fehlt)*
- [ ] 3.2 Implement structural vs soft field diffing
- [ ] 3.3 Implement conflict state handling

## 4. Idempotency and Loop Prevention

- [x] 4.1 Implement payload hash comparison *(Hash-Vergleich gegen `last_synced_hash` in `sync_service.py`)*
- [ ] 4.2 Implement outbound revision tracking
- [ ] 4.3 Implement inbound revision guard

## 5. Delete Handling

- [ ] 5.1 Implement MARK_CANCELLED behavior
- [ ] 5.2 Implement HARD_DELETE behavior

## 6. Integration Tests

- [ ] 6.1 Test duplicate webhook handling
- [ ] 6.2 Test concurrent internal/external modification
- [ ] 6.3 Test delete behavior modes
