# Field-Level Sync Authority Specification

> **Status:** Draft - Based on gap analysis findings  
> **OpenSpec Change:** planning-slot-hybrid-sync  
> **Related:** hybrid-calendar-sync, external-event-ingestion  
> **Priority:** 🔴 CRITICAL - Currently NOT implemented

---

## Overview

This specification defines **field-level authority rules** for calendar synchronization, ensuring that external systems cannot modify fields that are under internal governance control.

### Problem Statement

Currently, `sync_service.py` (lines 85-105) updates **ALL** event fields directly from external sources without any authority checks:

```python
# Current implementation - VIOLATES this spec
existing.title = raw.title        # Should be STRUCTURAL -> NOT allowed
existing.start_at = raw.start_at  # Should be CONDITIONAL -> Set deviation_flag
existing.end_at = raw.end_at      # Should be CONDITIONAL -> Set deviation_flag
existing.description = raw.description  # Should be SOFT -> Allowed
existing.congregation_id = raw.congregation_id  # Should be STRUCTURAL -> NOT allowed
```

This allows external systems to **override structural decisions** made by district planners.

---

## Field Classification

### 1. STRUCTURAL Fields (❌ Never Externally Mutable)

Fields that define the **normative planning structure** and are **solely controlled by internal governance**.

| Field | Entity | Reason | External Behavior |
|-------|--------|--------|------------------|
| `id` | All | Primary key | IGNORE external changes |
| `district_id` | Event, PlanningSlot, PlanningSeries | District ownership | IGNORE external changes |
| `congregation_id` | Event, PlanningSlot, PlanningSeries | Congregation assignment | IGNORE external changes |
| `category` | Event, PlanningSlot | Service type classification | IGNORE external changes |
| `series_id` | PlanningSlot | Series membership | IGNORE external changes |
| `status` | PlanningSlot | Planning status (ACTIVE/CANCELLED) | IGNORE external changes |
| `approval_status` | Event | Internal workflow status | IGNORE external changes |
| `source` | Event, EventInstance | Source classification | IGNORE external changes |
| `visibility` | Event, EventInstance | Visibility rules | IGNORE external changes |

**Rule:** If external system attempts to modify a STRUCTURAL field, the change **MUST BE IGNORED** and logged as a governance violation.

---

### 2. CONDITIONAL Fields (⚠️ Externally Mutable with Deviation Tracking)

Fields that **can** be modified externally, but changes represent **deviations from the normative plan**.

| Field | Entity | Reason | External Behavior |
|-------|--------|--------|------------------|
| `start_at` | Event, EventInstance | Actual execution time | ACCEPT change, set `deviation_flag = true` |
| `end_at` | Event, EventInstance | Actual execution time | ACCEPT change, set `deviation_flag = true` |
| `planning_date` | PlanningSlot | **NEVER** - structural | IGNORE (this is a bug if attempted) |
| `planning_time` | PlanningSlot | **NEVER** - structural | IGNORE (this is a bug if attempted) |

**Rule:** If external system modifies a CONDITIONAL field:
1. ACCEPT the change
2. Set `deviation_flag = true` on the EventInstance
3. Store the original planned value for display
4. Create a Notification of type `EXTERNAL_TIME_DEVIATION`

---

### 3. SOFT Fields (✅ Externally Mutable)

Fields that **can** be modified externally without governance implications.

| Field | Entity | Reason | External Behavior |
|-------|--------|--------|------------------|
| `title` | Event, EventInstance | Event title | ACCEPT change |
| `description` | Event, EventInstance | Event description | ACCEPT change |
| `location` | Event | Event location | ACCEPT change |
| `external_uid` | Event | External system identifier | ACCEPT change (if from same source) |
| `content_hash` | Event | Content fingerprint | ACCEPT change |

**Rule:** If external system modifies a SOFT field, the change **MUST BE ACCEPTED** without deviation tracking.

---

## Authority Enforcement Rules

### Rule 1: Field Classification Lookup

```python
# Pseudocode for field authority lookup
FIELD_AUTHORITY = {
    # STRUCTURAL fields
    (Event, 'district_id'): FieldAuthority.STRUCTURAL,
    (Event, 'congregation_id'): FieldAuthority.STRUCTURAL,
    (Event, 'category'): FieldAuthority.STRUCTURAL,
    (Event, 'approval_status'): FieldAuthority.STRUCTURAL,
    (Event, 'source'): FieldAuthority.STRUCTURAL,
    (Event, 'visibility'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'district_id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'congregation_id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'series_id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'category'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'planning_date'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'planning_time'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'status'): FieldAuthority.STRUCTURAL,
    
    # CONDITIONAL fields
    (Event, 'start_at'): FieldAuthority.CONDITIONAL,
    (Event, 'end_at'): FieldAuthority.CONDITIONAL,
    (EventInstance, 'actual_start_at'): FieldAuthority.CONDITIONAL,
    (EventInstance, 'actual_end_at'): FieldAuthority.CONDITIONAL,
    
    # SOFT fields
    (Event, 'title'): FieldAuthority.SOFT,
    (Event, 'description'): FieldAuthority.SOFT,
    (Event, 'location'): FieldAuthority.SOFT,
    (Event, 'external_uid'): FieldAuthority.SOFT,
    (Event, 'content_hash'): FieldAuthority.SOFT,
    (EventInstance, 'title'): FieldAuthority.SOFT,
    (EventInstance, 'description'): FieldAuthority.SOFT,
}
```

### Rule 2: Sync Processing Logic

```python
# Pseudocode for authority enforcement in sync_service.py

def process_external_event_update(existing_event: Event, raw_event: RawCalendarEvent) -> tuple[Event, bool]:
    """
    Process external event update with field-level authority.
    Returns: (updated_event, has_deviation)
    """
    has_deviation = False
    
    for field_name, new_value in raw_event.dict().items():
        authority = FIELD_AUTHORITY.get((type(existing_event).__name__, field_name))
        
        if authority == FieldAuthority.STRUCTURAL:
            # IGNORE external changes to structural fields
            logger.warning(
                f"Governance violation: External system attempted to modify "
                f"STRUCTURAL field '{field_name}' on event {existing_event.id}"
            )
            # Create audit log entry
            create_audit_log(
                action="GOVERNANCE_VIOLATION",
                entity_type="Event",
                entity_id=existing_event.id,
                field=field_name,
                attempted_value=new_value,
                current_value=getattr(existing_event, field_name)
            )
            continue
            
        elif authority == FieldAuthority.CONDITIONAL:
            # ACCEPT change but track deviation
            old_value = getattr(existing_event, field_name)
            if old_value != new_value:
                setattr(existing_event, field_name, new_value)
                has_deviation = True
                
        elif authority == FieldAuthority.SOFT:
            # ACCEPT change without deviation tracking
            setattr(existing_event, field_name, new_value)
        
        else:
            # Unknown field - log warning but accept
            logger.warning(f"Unknown field authority for {field_name}")
            setattr(existing_event, field_name, new_value)
    
    return existing_event, has_deviation
```

### Rule 3: Deviation Flag Management

When a CONDITIONAL field is modified:

1. **For EventInstance:**
   - Set `deviation_flag = true`
   - Store original planned time in a separate field or audit log
   
2. **For Event (legacy):**
   - If `generation_slot_key` exists, find the corresponding PlanningSlot
   - Create or update EventInstance with `deviation_flag = true`
   - Store the external time in EventInstance.actual_start_at/actual_end_at

3. **Create Notification:**
   - Type: `EXTERNAL_TIME_DEVIATION`
   - Severity: WARNING
   - Target: District Admin and affected Congregation Admin
   - Content: "External system modified event time: [event_title] at [new_time] (planned: [planned_time])"

---

## Implementation Requirements

### 1. FieldAuthority Enum

```python
# app/domain/models/field_authority.py

from enum import Enum

class FieldAuthority(str, Enum):
    """Field-level authority classification for sync operations."""
    
    STRUCTURAL = "STRUCTURAL"
    # Never externally mutable. Defines normative planning structure.
    # Changes from external systems MUST BE IGNORED.
    
    CONDITIONAL = "CONDITIONAL"
    # Externally mutable but represents deviation from plan.
    # Changes MUST BE ACCEPTED and deviation_flag SET.
    
    SOFT = "SOFT"
    # Externally mutable without governance implications.
    # Changes MUST BE ACCEPTED without deviation tracking.
```

### 2. Authority Mapping Configuration

```python
# app/application/field_authority_config.py

from app.domain.models.field_authority import FieldAuthority
from app.domain.models.event import Event
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.event_instance import EventInstance

# Centralized field authority mapping
FIELD_AUTHORITY_MAP: dict[tuple[type, str], FieldAuthority] = {
    # Event - STRUCTURAL
    (Event, 'id'): FieldAuthority.STRUCTURAL,
    (Event, 'district_id'): FieldAuthority.STRUCTURAL,
    (Event, 'congregation_id'): FieldAuthority.STRUCTURAL,
    (Event, 'category'): FieldAuthority.STRUCTURAL,
    (Event, 'approval_status'): FieldAuthority.STRUCTURAL,
    (Event, 'source'): FieldAuthority.STRUCTURAL,
    (Event, 'visibility'): FieldAuthority.STRUCTURAL,
    
    # Event - CONDITIONAL
    (Event, 'start_at'): FieldAuthority.CONDITIONAL,
    (Event, 'end_at'): FieldAuthority.CONDITIONAL,
    
    # Event - SOFT
    (Event, 'title'): FieldAuthority.SOFT,
    (Event, 'description'): FieldAuthority.SOFT,
    (Event, 'location'): FieldAuthority.SOFT,
    (Event, 'external_uid'): FieldAuthority.SOFT,
    (Event, 'content_hash'): FieldAuthority.SOFT,
    (Event, 'calendar_integration_id'): FieldAuthority.SOFT,
    
    # PlanningSlot - ALL STRUCTURAL (aggregate root)
    (PlanningSlot, 'id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'district_id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'congregation_id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'series_id'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'category'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'planning_date'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'planning_time'): FieldAuthority.STRUCTURAL,
    (PlanningSlot, 'status'): FieldAuthority.STRUCTURAL,
    
    # EventInstance - CONDITIONAL
    (EventInstance, 'actual_start_at'): FieldAuthority.CONDITIONAL,
    (EventInstance, 'actual_end_at'): FieldAuthority.CONDITIONAL,
    
    # EventInstance - SOFT
    (EventInstance, 'title'): FieldAuthority.SOFT,
    (EventInstance, 'description'): FieldAuthority.SOFT,
    (EventInstance, 'source'): FieldAuthority.STRUCTURAL,
    (EventInstance, 'visibility'): FieldAuthority.STRUCTURAL,
    (EventInstance, 'deviation_flag'): FieldAuthority.STRUCTURAL,  # Internal only
    (EventInstance, 'planning_slot_id'): FieldAuthority.STRUCTURAL,  # Internal only
}

def get_field_authority(entity_type: type, field_name: str) -> FieldAuthority | None:
    """Get field authority for a given entity type and field name."""
    return FIELD_AUTHORITY_MAP.get((entity_type, field_name))
```

### 3. Authority Enforcer Service

```python
# app/application/field_authority_enforcer.py

from app.domain.models.field_authority import FieldAuthority
from app.domain.models.event import Event
from app.domain.models.event_instance import EventInstance
from app.application.field_authority_config import get_field_authority, FIELD_AUTHORITY_MAP
import logging

logger = logging.getLogger(__name__)

class FieldAuthorityEnforcer:
    """Enforces field-level authority rules during sync operations."""
    
    @staticmethod
    def enforce_field_update(
        entity: Event | EventInstance,
        field_name: str,
        new_value: any,
        source: str = "external"
    ) -> tuple[bool, bool]:
        """
        Enforce field-level authority for a field update.
        
        Args:
            entity: The entity being updated
            field_name: The field being modified
            new_value: The new value from external source
            source: The source of the change ('external' or 'internal')
        
        Returns:
            tuple: (should_apply_change, is_deviation)
        """
        if source != "external":
            # Internal changes always allowed
            return True, False
        
        authority = get_field_authority(type(entity), field_name)
        
        if authority is None:
            # Unknown field - log warning but allow
            logger.warning(f"Unknown field authority for {type(entity).__name__}.{field_name}")
            return True, False
        
        if authority == FieldAuthority.STRUCTURAL:
            # NEVER allow external modification of structural fields
            current_value = getattr(entity, field_name)
            logger.warning(
                f"Governance violation: External system attempted to modify "
                f"STRUCTURAL field '{field_name}' on {type(entity).__name__} {entity.id}. "
                f"Attempted: {new_value}, Current: {current_value}"
            )
            return False, False
        
        elif authority == FieldAuthority.CONDITIONAL:
            # Allow change but mark as deviation
            current_value = getattr(entity, field_name)
            if current_value != new_value:
                logger.info(
                    f"Conditional field '{field_name}' modified on {type(entity).__name__} {entity.id}. "
                    f"Old: {current_value}, New: {new_value}"
                )
                return True, True
            return True, False
        
        else:  # SOFT
            # Allow change without deviation tracking
            return True, False
```

### 4. Integration with Sync Service

```python
# app/application/sync_service.py - Updated with authority enforcement

from app.application.field_authority_enforcer import FieldAuthorityEnforcer

async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> dict[str, int]:
    """Sync one integration with field-level authority enforcement."""
    # ... existing setup code ...
    
    created = updated = cancelled = deviations = governance_violations = 0
    
    for raw in raw_events:
        existing = await event_repo.get_by_external_uid(raw.uid, integration.id)
        
        if existing is None:
            # New external event - create ExternalEventCandidate (future implementation)
            # For now, create Event directly (legacy behavior)
            event = Event.create(
                title=raw.title,
                start_at=raw.start_at,
                end_at=raw.end_at,
                description=raw.description,
                district_id=integration.district_id,
                congregation_id=integration.congregation_id,
                source=EventSource.EXTERNAL,
                status=EventStatus.DRAFT,
                visibility=EventVisibility.INTERNAL,
                external_uid=raw.uid,
                calendar_integration_id=integration.id,
                content_hash=raw.content_hash,
                category=integration.default_category,
            )
            await event_repo.save(event)
            created += 1
        
        else:
            if raw.is_cancelled and existing.status != EventStatus.CANCELLED:
                # Deletion handling
                existing.status = EventStatus.CANCELLED
                existing.updated_at = datetime.now(UTC)
                await event_repo.save(existing)
                cancelled += 1
            
            elif not raw.is_cancelled and existing.content_hash != raw.content_hash:
                # Update with authority enforcement
                has_deviation = False
                changes_applied = {}
                
                # Check each field with authority enforcer
                for field_name, new_value in [
                    ('title', raw.title),
                    ('start_at', raw.start_at),
                    ('end_at', raw.end_at),
                    ('description', raw.description),
                    ('congregation_id', integration.congregation_id),
                    ('category', integration.default_category),
                ]:
                    should_apply, is_deviation = FieldAuthorityEnforcer.enforce_field_update(
                        existing, field_name, new_value, source="external"
                    )
                    
                    if should_apply:
                        setattr(existing, field_name, new_value)
                        changes_applied[field_name] = (getattr(existing, field_name), new_value)
                    
                    if is_deviation:
                        has_deviation = True
                
                if changes_applied:
                    # Apply auto-categorization on update
                    existing.apply_auto_categorization()
                    
                    existing.content_hash = raw.content_hash
                    existing.updated_at = datetime.now(UTC)
                    await event_repo.save(existing)
                    updated += 1
                
                if has_deviation:
                    deviations += 1
                    # TODO: Create deviation notification when Notification system is implemented
                    logger.info(f"Deviation detected for event {existing.id}")
    
    # ... existing cleanup code ...
    
    return {
        "created": created,
        "updated": updated,
        "cancelled": cancelled,
        "deviations": deviations,
        "governance_violations": governance_violations
    }
```

---

## Testing Requirements

### Unit Tests

```python
# tests/unit/application/test_field_authority_enforcer.py

import pytest
from app.domain.models.field_authority import FieldAuthority
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.application.field_authority_enforcer import FieldAuthorityEnforcer
from datetime import datetime, UTC
import uuid


@pytest.fixture
def sample_event():
    return Event.create(
        title="Test Event",
        start_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        end_at=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        district_id=uuid.uuid4(),
        congregation_id=uuid.uuid4(),
        category="Gottesdienst",
        source=EventSource.INTERNAL,
        status=EventStatus.DRAFT,
        visibility=EventVisibility.INTERNAL,
    )


class TestFieldAuthorityEnforcer:
    def test_structural_field_rejected(self, sample_event):
        """STRUCTURAL fields should be rejected from external source."""
        should_apply, is_deviation = FieldAuthorityEnforcer.enforce_field_update(
            sample_event, 'district_id', uuid.uuid4(), source="external"
        )
        assert should_apply is False
        assert is_deviation is False
    
    def test_conditional_field_accepted_with_deviation(self, sample_event):
        """CONDITIONAL fields should be accepted and flagged as deviation."""
        new_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        should_apply, is_deviation = FieldAuthorityEnforcer.enforce_field_update(
            sample_event, 'start_at', new_time, source="external"
        )
        assert should_apply is True
        assert is_deviation is True
    
    def test_soft_field_accepted_without_deviation(self, sample_event):
        """SOFT fields should be accepted without deviation flag."""
        should_apply, is_deviation = FieldAuthorityEnforcer.enforce_field_update(
            sample_event, 'title', "New Title", source="external"
        )
        assert should_apply is True
        assert is_deviation is False
    
    def test_internal_changes_always_allowed(self, sample_event):
        """Internal changes should always be allowed."""
        should_apply, is_deviation = FieldAuthorityEnforcer.enforce_field_update(
            sample_event, 'district_id', uuid.uuid4(), source="internal"
        )
        assert should_apply is True
        assert is_deviation is False
```

### Integration Tests

```python
# tests/integration/test_sync_field_authority.py

import pytest
from app.application.sync_service import run_sync
from app.domain.models.event import Event, EventSource, EventStatus
from app.domain.models.calendar_integration import CalendarIntegration, CalendarType
import uuid


@pytest.mark.asyncio
async def test_sync_respects_field_authority(async_session):
    """Test that sync respects field-level authority rules."""
    # Setup: Create integration and event
    integration = CalendarIntegration(
        id=uuid.uuid4(),
        district_id=uuid.uuid4(),
        congregation_id=uuid.uuid4(),
        type=CalendarType.GOOGLE,
        # ... other fields
    )
    
    event = Event.create(
        title="Original Title",
        start_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        end_at=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        district_id=integration.district_id,
        congregation_id=uuid.uuid4(),  # Different from integration
        category="Gottesdienst",
        source=EventSource.EXTERNAL,
        status=EventStatus.DRAFT,
        external_uid="ext-123",
        calendar_integration_id=integration.id,
        content_hash="old-hash",
    )
    
    # Save to DB
    async_session.add(integration)
    async_session.add(event)
    await async_session.commit()
    
    # Create raw event with changes
    class MockRawEvent:
        uid = "ext-123"
        title = "Modified Title"  # SOFT - should be accepted
        start_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)  # CONDITIONAL - should be accepted with deviation
        end_at = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)  # CONDITIONAL - should be accepted with deviation
        description = "New description"  # SOFT - should be accepted
        is_cancelled = False
        content_hash = "new-hash"
    
    # Mock connector to return our raw event
    # ... setup mock ...
    
    # Run sync
    result = await run_sync(integration.id, async_session)
    
    # Verify results
    assert result["updated"] == 1
    assert result["deviations"] == 1  # start_at and end_at changes
    
    # Reload event
    await async_session.refresh(event)
    
    # SOFT fields should be updated
    assert event.title == "Modified Title"
    assert event.description == "New description"
    
    # CONDITIONAL fields should be updated
    assert event.start_at == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    assert event.end_at == datetime(2024, 1, 1, 13, 0, tzinfo=UTC)
    
    # STRUCTURAL fields should NOT be updated
    # congregation_id should remain unchanged (not updated from integration.congregation_id)
    assert event.congregation_id != integration.congregation_id
```

---

## Migration Path

### Phase 1: Implement FieldAuthority Infrastructure (1 Woche)
1. Create `FieldAuthority` enum
2. Create `FIELD_AUTHORITY_MAP` configuration
3. Create `FieldAuthorityEnforcer` service
4. Add unit tests

### Phase 2: Integrate with Sync Service (1 Woche)
1. Update `sync_service.py` to use FieldAuthorityEnforcer
2. Add deviation tracking
3. Add governance violation logging
4. Add integration tests

### Phase 3: Add Audit Logging (1 Woche)
1. Create AuditLog entity
2. Log all governance violations
3. Log all deviation events
4. Create audit log API

### Phase 4: Add Notifications (1 Woche)
1. Implement Notification system
2. Create deviation notifications
3. Create governance violation notifications

---

## Related Specifications

- [Hybrid Calendar Sync Spec](../hybrid-calendar-sync/spec.md)
- [External Event Ingestion Spec](../external-event-ingestion/spec.md)
- [In-App Notifications Spec](../in-app-notifications/spec.md)
- [RBAC Model Spec](../../introduce-rbac-permissions-model/specs/rbac-model/spec.md)

---

## Open Questions

1. **Field Classification:** Are there any fields that should be reclassified?
   - Should `category` be SOFT if external systems provide better categorization?
   - Should `congregation_id` ever be updatable from external sources?

2. **Deviation Thresholds:** Should there be thresholds for deviation notifications?
   - E.g., only notify if time deviation > 15 minutes?
   - E.g., only notify if time deviation > 1 hour?

3. **Governance Violation Handling:** What should happen on repeated governance violations?
   - Log only?
   - Disable integration?
   - Notify superadmin?

4. **Audit Log Retention:** How long should governance violation logs be retained?

---

*This specification addresses the critical gap identified in the OpenSpec gap analysis.*
*Field-level authority enforcement is essential for maintaining governance control over the planning model.*
