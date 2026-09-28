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

- [x] 3.1 Implement sync state transition logic *(formale State-Machine `inbound_state()`/`internal_state()` in `domain/services/sync_policy.py`; alle CLEAN/DIRTY_INTERNAL/DIRTY_EXTERNAL/CONFLICT-Übergänge abgedeckt)*
- [x] 3.2 Implement structural vs soft field diffing
- [x] 3.3 Implement conflict state handling *(Konflikt-Zustand über `inbound_state()`/`internal_state()` erreichbar und persistiert; REST-Endpoint zur Auflösung von Feldkonflikten steht noch aus und wird als eigene Aufgabe getrackt)*
- [ ] 3.4 Expose CONFLICT state and resolution endpoint to PLANNER *(aktuell bleibt ein Konflikt ohne UI/Endpoint unerkannt; Hash wird bewusst nicht aktualisiert, sodass jede Sync-Runde erneut konfligiert)*

## 4. Idempotency and Loop Prevention

- [x] 4.1 Implement payload hash comparison *(Hash-Vergleich gegen `last_synced_hash` in `sync_service.py`)*
- [x] 4.2 Implement outbound revision tracking
- [x] 4.3 Implement inbound revision guard

## 5. Delete Handling

- [x] 5.1 Implement MARK_CANCELLED behavior
- [x] 5.2 Implement HARD_DELETE behavior

## 6. Integration Tests

- [x] 6.1 Test duplicate webhook handling
- [x] 6.2 Test concurrent internal/external modification
- [x] 6.3 Test delete behavior modes
