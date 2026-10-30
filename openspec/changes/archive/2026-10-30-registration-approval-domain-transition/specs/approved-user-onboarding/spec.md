## ADDED Requirements

### Requirement: Registration approval state transition SHALL be centralized in the domain
A registration SHALL only transition from `PENDING` to `APPROVED` using the domain model's approval operation, which MUST set role, scope, approving subject, approval timestamp and update timestamp together. The operation SHALL reset prior provisioning status and error fields and MUST reject non-pending registrations without modifying them.

#### Scenario: Approving a pending registration
- **WHEN** a district admin approves a pending registration with role, scope and actor
- **THEN** the domain changes status to APPROVED and stores all authorization metadata and timestamps together

#### Scenario: Attempting to approve an already resolved registration
- **WHEN** an approval operation is attempted for an approved or rejected registration
- **THEN** the domain rejects the operation without mutating its current state

#### Scenario: Existing transactional effects preserved
- **WHEN** leader persistence or membership linking fails during approval
- **THEN** the request transaction rolls back as before and no after-commit event is published
