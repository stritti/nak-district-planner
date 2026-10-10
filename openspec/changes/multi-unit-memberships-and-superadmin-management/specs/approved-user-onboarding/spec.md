## MODIFIED Requirements

### Requirement: Registration approval SHALL activate user access explicitly

The system SHALL treat self-registration and access activation as separate steps. A registered non-superadmin user MUST NOT gain access to protected business endpoints until an authorized administrator approves the registration and assigns an authorization scope. A user explicitly granted superadmin status by an existing superadmin SHALL have global access without an approval-created membership, consistent with the existing superadmin exception. If that status is later revoked and no approved effective membership exists, protected business access SHALL revert to 403 and the pending/no-access client state, regardless of any earlier registration state.

#### Scenario: Registered but not approved user logs in

- **WHEN** a non-superadmin user authenticates successfully via OIDC but has no approved access assignment
- **THEN** protected business endpoints return 403 Forbidden
- **AND** the response indicates that approval is pending

#### Scenario: District admin approves registration

- **WHEN** a district admin approves a pending registration within their authorized scope
- **THEN** the registration status changes to APPROVED
- **AND** approval metadata (approved_by_sub, approved_at) is stored

#### Scenario: Appointed superadmin has no memberships

- **WHEN** a registered user securely linked to an authenticated subject has been appointed superadmin by an existing superadmin
- **THEN** protected business endpoints allow global access without requiring a membership
- **AND** the frontend does not treat the user as pending approval solely because their membership list is empty

## ADDED Requirements

### Requirement: Administrators can manage additional unit assignments

Superadmins SHALL be able to add, update and remove district and congregation memberships of registered, securely linked users across all units. Non-superadmins MAY grant only roles no higher than their own within the same authorised scope; a congregation administrator MUST NOT grant a district-scoped membership. Other authorized administrators SHALL be able to manage assignments only within their existing management permissions. Additional assignments SHALL use the existing role, scope_type and scope_id fields and SHALL preserve the user's existing account and other memberships. Secure user-linkage requirements SHALL remain applicable.

#### Scenario: Superadmin adds a second assignment

- **WHEN** a superadmin adds a membership in another congregation or district to an already linked user
- **THEN** both the previous and new assignments remain available for that same user account

#### Scenario: Congregation administrator attempts district membership
- **WHEN** a congregation administrator attempts to grant a district-scoped role even inside the parent district
- **THEN** the request is rejected with 403 and no membership is modified

#### Scenario: Administrator assigns outside their authority

- **WHEN** a non-superadmin administrator attempts to assign a user to a unit outside their management permissions
- **THEN** the request returns 403 Forbidden
- **AND** existing memberships remain unchanged
