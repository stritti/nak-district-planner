## ADDED Requirements

### Requirement: Sync transitions are explicit and validated
The system SHALL define legal synchronization state transitions in one provider-independent domain policy.

#### Scenario: Legal transition
- **WHEN** a classified sync event is valid for the current SyncState
- **THEN** the policy SHALL return the deterministic next state

#### Scenario: Illegal transition
- **WHEN** a transition is not defined for the current SyncState and command
- **THEN** the system SHALL reject it explicitly rather than silently assigning a state

### Requirement: Conflict detection follows change classification
The system SHALL classify externally changed fields before deciding whether concurrent internal and external changes constitute a conflict.

#### Scenario: External soft-only change with internal dirty state
- **WHEN** an EventInstance is DIRTY_INTERNAL and the provider changed only externally-authoritative SOFT fields
- **THEN** the system SHALL apply the permitted merge without creating a conflict solely because the payload hash changed

#### Scenario: Concurrent incompatible change
- **WHEN** internal and external changes affect incompatible authoritative data
- **THEN** the system SHALL transition to CONFLICT and retain sufficient information for explicit resolution

### Requirement: Field authority is entity scoped
The system SHALL classify field authority using both entity type and field identity.

#### Scenario: Same field name on different entities
- **WHEN** two domain entities expose fields with the same name but different governance semantics
- **THEN** their authority SHALL be independently configurable and testable

### Requirement: PlanningSlot remains aggregate root
Sync state and deviation changes SHALL respect the PlanningSlot aggregate boundary.

#### Scenario: Sync applies EventInstance change
- **WHEN** the sync engine accepts an external change for an EventInstance
- **THEN** aggregate validation SHALL occur before persistence and structural PlanningSlot fields SHALL remain internally authoritative
