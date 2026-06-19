# Matrix Rendering Migration Plan (Task Group 1.1)

## Problem Statement

**Confirmed by Domain Expert:** "Nein, Migration nicht abgeschlossen" (Migration NOT complete)

The matrix rendering in `services/backend/app/adapters/api/routers/districts.py` currently uses **DUAL SOURCES**:
- **Legacy:** `Event` model (event_by_owner_date)
- **New:** `PlanningSlot` + `EventInstance` models (slot_by_owner_date, instance_by_slot_id)

**Spec Requirement:** Matrix SHALL render using PlanningSlot as the authoritative source.

## Current Architecture Issues

### 1. Dual Data Sources
```python
# Lines 462-465: Load events (legacy)
events, _ = await SqlEventRepository(db).list(...)

# Lines 488-495: Load slots and instances (new)
slots = await SqlPlanningSlotRepository(db).list_for_date_range(...)
instances = await SqlEventInstanceRepository(db).list_by_planning_slots(...)
```

### 2. Fallback Logic Throughout
```python
# Lines 548-550: Event fallback for slots
slot = slot_by_owner_date.get((congregation.id, date_key))
if slot is None:
    slot = slot_by_owner_date.get((district_id, date_key))

# Lines 552-554: Event fallback for cells
if event is None and slot is None:
    cells[date_key] = MatrixCell()
    continue

# Lines 556-600: Multiple event fallbacks in MatrixCell creation
slot_or_event_id = slot.id if slot is not None else event.id
instance = instance_by_slot_id.get(slot.id) if slot is not None else None
assignment = assignment_by_slot_id.get(slot_or_event_id)
# ... and many more
```

### 3. Event-Specific Fields Used in Matrix
The following Event fields are used but don't exist on PlanningSlot/EventInstance:
- `event.invitation_source_congregation_id` (Line 595)
- `event.invitation_source_event_id` (Line 558, 562, 566)
- `event.approval_status` (Line 607)
- `event.title` (Line 591 - fallback when instance.title is None)
- `event.start_at` / `event.end_at` (Lines 593-602 - fallback)
- `event.category` (Line 603 - fallback)

### 4. Invitation System Coupled to Events
```python
# Lines 535-546: Invitation loading based on events
source_congregation_ids = {
    e.invitation_source_congregation_id
    for e in gottesdienst_events
    if e.invitation_source_congregation_id is not None
}
source_event_ids = [e.id for e in gottesdienst_events if e.invitation_source_event_id is None]
invitations = await SqlInvitationRepository(db).list_by_source_events(source_event_ids)
```

### 5. Holidays Still Stored as Events
```python
# Lines 471-475: Holidays from Event model
for event in events:
    if event.category == "Feiertag":
        date_key = event.start_at.date().isoformat()
        holidays.setdefault(date_key, []).append(event.title)
```

## Migration Strategy

### Phase 1: Prepare Data Models (Required First)
Before we can remove Event fallback, we need to ensure all data is available in PlanningSlot/EventInstance:

#### 1.1 Add Missing Fields to PlanningSlot/EventInstance
- [ ] Add `invitation_source_congregation_id` to PlanningSlot
- [ ] Add `invitation_source_event_id` to PlanningSlot (or EventInstance)
- [ ] Add `approval_status` to PlanningSlot
- [ ] Add `source` to PlanningSlot (currently only on EventInstance)

#### 1.2 Migrate Holidays to PlanningSlots
- [ ] Create migration script to convert Event(category="Feiertag") to PlanningSlot(category="Feiertag")
- [ ] Update feiertage_service.py to create PlanningSlots instead of Events
- [ ] Keep backward compatibility during transition

#### 1.3 Update Invitation System
- [ ] Add `source_planning_slot_id` to Invitation model
- [ ] Update invitation loading to work with PlanningSlots
- [ ] Migration: Copy invitation_source_event_id to source_planning_slot_id

### Phase 2: Update Matrix Rendering (This PR)
Once data models are ready, update the matrix rendering:

#### 2.1 Remove Event Loading for Matrix
```python
# REMOVE these lines:
events, _ = await SqlEventRepository(db).list(...)
gottesdienst_events = [event for event in events if event.category == "Gottesdienst"]
event_by_owner_date: dict[tuple[uuid.UUID, str], object] = {}
for event in gottesdienst_events:
    owner_id = event.congregation_id or event.district_id
    key = (owner_id, event.start_at.date().isoformat())
    existing_event = event_by_owner_date.get(key)
    if existing_event is None or event.start_at < existing_event.start_at:
        event_by_owner_date[key] = event
```

#### 2.2 Remove Event Fallback Logic
```python
# REMOVE event fallback:
event = event_by_owner_date.get((congregation.id, date_key))
if event is None:
    event = event_by_owner_date.get((district_id, date_key))
if event is None and date_key not in cong_expected:
    cells[date_key] = MatrixCell()
    continue

# CHANGE TO: Only use slots
slot = slot_by_owner_date.get((congregation.id, date_key))
if slot is None:
    slot = slot_by_owner_date.get((district_id, date_key))
if slot is None and date_key not in cong_expected:
    cells[date_key] = MatrixCell()
    continue
```

#### 2.3 Update MatrixCell Creation
Remove all `event` references and use only `slot` and `instance`:

```python
# BEFORE:
slot_or_event_id = slot.id if slot is not None else event.id
instance = instance_by_slot_id.get(slot.id) if slot is not None else None
assignment = assignment_by_slot_id.get(slot_or_event_id)
is_invitation_copy = event.invitation_source_event_id is not None if event else False
assignment_event_id = event.id if event is not None else slot_or_event_id

# AFTER:
slot_id = slot.id
instance = instance_by_slot_id.get(slot_id)
assignment = assignment_by_slot_id.get(slot_id)
is_invitation_copy = slot.invitation_source_event_id is not None
assignment_event_id = slot_id
```

#### 2.4 Update All MatrixCell Fields
```python
# BEFORE (with event fallbacks):
event_title=instance.title if instance is not None else event.title if event is not None else None
event_start_at=instance.actual_start_at if instance is not None else event.start_at if event is not None else None
category=slot.category if slot is not None else event.category if event is not None else None
approval_status=event.approval_status
planned_time=slot.planning_time if slot is not None else event.start_at.timetz().replace(tzinfo=None) if event is not None else None

# AFTER (slot/instance only):
event_title=instance.title if instance is not None else slot.title
event_start_at=instance.actual_start_at if instance is not None else slot.planning_time
category=slot.category
approval_status=slot.approval_status
planned_time=slot.planning_time
```

#### 2.5 Update Invitation Loading
```python
# BEFORE:
source_congregation_ids = {
    e.invitation_source_congregation_id
    for e in gottesdienst_events
    if e.invitation_source_congregation_id is not None
}
source_event_ids = [e.id for e in gottesdienst_events if e.invitation_source_event_id is None]
invitations = await SqlInvitationRepository(db).list_by_source_events(source_event_ids)

# AFTER:
source_congregation_ids = {
    slot.invitation_source_congregation_id
    for slot in gottesdienst_slots
    if slot.invitation_source_congregation_id is not None
}
source_slot_ids = [slot.id for slot in gottesdienst_slots if slot.invitation_source_slot_id is None]
invitations = await SqlInvitationRepository(db).list_by_source_slots(source_slot_ids)
```

### Phase 3: Frontend Updates
- [ ] Update MatrixView.vue to handle only PlanningSlot/EventInstance data
- [ ] Update matrix.ts API to use PlanningSlot endpoints
- [ ] Remove Event-specific UI logic

### Phase 4: Cleanup
- [ ] Remove Event repository calls from matrix endpoint
- [ ] Remove Event model imports from matrix endpoint
- [ ] Update tests to use only PlanningSlot/EventInstance

## Blockers

1. **Data Model Gaps**: PlanningSlot/EventInstance missing fields needed for matrix
2. **Invitation System**: Currently coupled to Event model
3. **Holidays**: Still stored as Events, need migration
4. **Backward Compatibility**: Existing data uses Event model

## Recommended Approach

Given the complexity and interdependencies, recommend:

1. **First**: Add missing fields to PlanningSlot/EventInstance (Phase 1.1)
2. **Second**: Create migration for Holidays to PlanningSlots (Phase 1.2)
3. **Third**: Update Invitation system (Phase 1.3)
4. **Fourth**: Update matrix rendering (Phase 2)
5. **Fifth**: Update frontend (Phase 3)

## Files to Modify

### Backend
- `services/backend/app/domain/models/planning_slot.py` - Add missing fields
- `services/backend/app/domain/models/event_instance.py` - Add missing fields
- `services/backend/app/domain/models/invitation.py` - Add source_planning_slot_id
- `services/backend/app/adapters/db/repositories/invitation.py` - Add list_by_source_slots
- `services/backend/app/application/feiertage_service.py` - Create PlanningSlots instead of Events
- `services/backend/app/adapters/api/routers/districts.py` - Remove Event fallback, use only PlanningSlot

### Frontend
- `services/frontend/src/views/MatrixView.vue` - Update to use PlanningSlot data
- `services/frontend/src/api/matrix.ts` - Update API calls

### Tests
- `services/backend/tests/unit/test_router_districts.py` - Update matrix tests
- `services/backend/tests/integration/test_matrix_endpoint.py` - Update integration tests

## Estimated Effort

| Phase | Task | Effort | Complexity |
|-------|------|--------|------------|
| 1.1 | Add fields to PlanningSlot/EventInstance | 2-4 hours | Medium |
| 1.2 | Migrate Holidays to PlanningSlots | 4-8 hours | High |
| 1.3 | Update Invitation system | 4-6 hours | High |
| 2 | Update matrix rendering | 6-8 hours | High |
| 3 | Update frontend | 4-6 hours | Medium |
| 4 | Cleanup and tests | 4-8 hours | Medium |
| **Total** | | **24-40 hours** | |

## Decision Required

Given the complexity, should we:

**Option A**: Full migration now (24-40 hours)
- Complete all phases
- Remove all Event dependencies from matrix
- Clean architecture

**Option B**: Incremental migration
- Phase 1: Add fields to models
- Phase 2: Migrate holidays
- Phase 3: Update matrix rendering
- Phase 4: Update frontend

**Option C**: Hybrid approach (Recommended)
- Keep Event loading for holidays only
- Remove Event fallback for Gottesdienst
- Use PlanningSlot/EventInstance as primary source
- Gradually migrate holidays

**Recommendation**: Option C (Hybrid) for now, then full migration later.
