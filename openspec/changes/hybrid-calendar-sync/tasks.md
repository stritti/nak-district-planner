## 1. Field Classification

- [ ] 1.1 Define `SyncFieldAuthority` enum (STRUCTURAL, SOFT, CONDITIONAL) in domain model
- [ ] 1.2 Implement field-to-authority mapping for all PlanningSlot and EventInstance fields
- [ ] 1.3 Implement classifier function in sync pipeline that routes fields by authority
- [ ] 1.4 Default unclassified fields to STRUCTURAL with warning log

## 2. Deviation Detection & Storage

- [ ] 2.1 Implement deviation detection logic (compare incoming time vs PlanningSlot.planning_time)
- [ ] 2.2 Store external time changes in EventInstance.actual_start/actual_end
- [ ] 2.3 Set EventInstance.deviation_flag = true on time deviation
- [ ] 2.4 Implement deviation resolution endpoint (POST /api/v1/...)

## 3. Symmetric Deletion

- [ ] 3.1 Implement external deletion → soft-delete PlanningSlot + EventInstance (cancelled status)
- [ ] 3.2 Implement internal deletion → push deletion to external CalendarConnector
- [ ] 3.3 Implement deletion loop prevention (track origin, ignore self-initiated deletions)

## 4. Tests

- [ ] 4.1 Unit tests for field classification logic
- [ ] 4.2 Unit tests for deviation detection and storage
- [ ] 4.3 Unit tests for symmetric deletion propagation
- [ ] 4.4 Unit tests for deletion loop prevention
