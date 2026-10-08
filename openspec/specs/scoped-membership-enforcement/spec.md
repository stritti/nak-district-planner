## ADDED Requirements

### Requirement: Protected endpoints SHALL require effective memberships
The system SHALL deny access to protected business endpoints when an authenticated user has no effective memberships, except for superadmin users.

#### Scenario: Authenticated user without memberships accesses protected endpoint
- **WHEN** a valid authenticated user has zero memberships
- **THEN** system returns `403 Forbidden`
- **AND** no business data is returned

#### Scenario: Superadmin without memberships accesses protected endpoint
- **WHEN** an authenticated user is marked as superadmin
- **THEN** system allows access according to superadmin semantics

### Requirement: District-scoped access SHALL be enforced by membership scope
The system SHALL allow district-level operations only when user memberships satisfy required role hierarchy within the target district.

#### Scenario: User has required district role
- **WHEN** user has membership in `DISTRICT` scope matching requested district and role hierarchy >= required role
- **THEN** operation is authorized

#### Scenario: User has role in different district
- **WHEN** user has district membership for district A but requests operation in district B
- **THEN** operation is rejected with `403 Forbidden`

### Requirement: Congregation-scoped access SHALL be enforced by membership scope
The system SHALL allow congregation-level operations only when user memberships satisfy required role hierarchy within the target congregation.

#### Scenario: User has required congregation role
- **WHEN** user has membership in `CONGREGATION` scope matching requested congregation and role hierarchy >= required role
- **THEN** operation is authorized

#### Scenario: User lacks matching congregation scope
- **WHEN** user has memberships only outside the requested congregation
- **THEN** operation is rejected with `403 Forbidden`

### Requirement: Access context SHALL be visible for client UX
The system SHALL provide an authenticated endpoint that returns effective memberships so the client can render access-aware UI states.

#### Scenario: Client requests access context
- **WHEN** authenticated client calls the access-context endpoint
- **THEN** response includes effective memberships with `role`, `scope_type`, and `scope_id`

#### Scenario: Client requests access context while pending approval
- **WHEN** authenticated client has no memberships and is not superadmin
- **THEN** endpoint responds successfully with an empty membership list
- **AND** client can show "Freigabe ausstehend" state

### Requirement: Pending registration visibility SHALL be prominent for admin roles
The system SHALL provide immediate visibility of open registrations for superadmin and district-admin users after login.

#### Scenario: Superadmin logs in with open registrations
- **WHEN** authenticated superadmin has open registrations in one or more districts
- **THEN** client receives pending counts via overview endpoint
- **AND** global UI shows a prominent open-registration indicator

#### Scenario: District admin logs in with open registrations in managed districts
- **WHEN** authenticated district admin has open registrations in districts where they hold `DISTRICT_ADMIN`
- **THEN** overview returns counts for those districts only
- **AND** global UI shows a prominent open-registration indicator
