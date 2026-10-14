## 1. API and State

- [x] 1.1 Add typed candidate API client
- [x] 1.2 Add Pinia store for district-scoped pending candidates
- [x] 1.3 Refresh the list after accept/dismiss mutations

## 2. Review UI

- [x] 2.1 Add authenticated `/admin/external-candidates` route
- [x] 2.2 Add candidate review view with loading, empty, error, and mutation states
- [x] 2.3 Support "accept and create PlanningSlot"
- [x] 2.4 Support dismiss
- [x] 2.5 Existing PlanningSlot selection is deferred to a follow-up with searchable slot discovery *(zurückgestellt → Backlog; die API unterstützt `matched_slot_id` bereits, siehe Spec `external-event-ingestion`)*

## 3. Navigation

- [x] 3.1 Route candidate-review notifications to the review page
- [x] 3.2 Add admin navigation entry

## 4. Tests

- [x] 4.1 Add API client tests
- [x] 4.2 Add store mutation/error tests
- [x] 4.3 Add view tests for empty, loading, accept, dismiss, and error paths
