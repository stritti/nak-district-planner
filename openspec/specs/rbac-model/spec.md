# rbac-model Specification

## Purpose

Defines the role model and the permission helpers every router uses (`app/adapters/auth/permissions.py`). Memberships bind a user (`sub`) to a role within a district or congregation scope; superadmins bypass scope checks. See `docs/roles.md` for the permission matrix.

## Requirements

### Requirement: Canonical role hierarchy
The system SHALL know exactly the roles `DISTRICT_ADMIN` > `CONGREGATION_ADMIN` > `PLANNER` > `VIEWER`; a higher role SHALL imply every permission of the lower roles. Roles SHALL be stored per user as `Membership` rows with `scope_type` (`DISTRICT` | `CONGREGATION`) and `scope_id`.

#### Scenario: Planner performs a viewer action
- **WHEN** a user with `PLANNER` in a district calls an endpoint requiring `VIEWER` there
- **THEN** access is granted

### Requirement: Scoped permission checks
`has_role_in_district` SHALL grant access for a matching district membership with sufficient role and, only when the caller passes the relevant congregation IDs, for a matching congregation membership. `has_role_in_congregation` SHALL consider congregation memberships of that congregation. Routers SHALL translate failed checks into HTTP 403 (`require_role_in_district`).

#### Scenario: Role in a different district
- **WHEN** a user holds `DISTRICT_ADMIN` in district A and calls a district-admin endpoint of district B
- **THEN** the API responds with 403

#### Scenario: Viewer attempts a write
- **WHEN** a `VIEWER` patches a planning slot
- **THEN** the API responds with 403 and the slot is unchanged

### Requirement: Superadmin

Users with is_superadmin SHALL have global access to all districts, congregations, business data and administrative functions, including management of registered users and appointment of further superadmins. They SHALL pass all role and scope checks without requiring memberships; no pre-router middleware makes tenant authorization decisions. Only superadmins SHALL create districts and list cross-district resources without a district filter; business validation still applies.

#### Scenario: Cross-district listing

- **WHEN** a superadmin lists events without district_id
- **THEN** the request is allowed and can include events across all districts

#### Scenario: Superadmin accesses an unassigned unit

- **WHEN** a superadmin without memberships accesses or administers a district or congregation
- **THEN** the action is authorized and the target data is available according to the requested operation

#### Scenario: Selected context does not limit authorization

- **WHEN** a superadmin has selected district A in the interface and requests an administrative action in district B
- **THEN** the selected context does not prevent authorization in district B

### Requirement: Superadmin status is read from the database

The flag MUST be loaded from the current database user record of the verified subject on every request and set in transaction-local RLS context. Token claims, the bootstrap helper's result or frontend state SHALL NOT grant it. Global access SHALL apply consistently in API authorization, row-level security and frontend visibility. Changes to the flag SHALL use an audited, minimally privileged transactional database operation; the application DB role MUST NOT update `users.is_superadmin` directly.

#### Scenario: Appointed superadmin authenticates after bootstrap

- **WHEN** an appointed superadmin whose subject differs from the configured bootstrap subject authenticates
- **THEN** the current persisted superadmin status remains true and global access is granted
- **AND** logging in as the bootstrap subject does not revoke the appointed status

#### Scenario: Bootstrap helper returns false for an unrelated subject

- **WHEN** a previously appointed superadmin authenticates and the bootstrap helper does not initialize a new grant
- **THEN** authorization still uses the persisted `is_superadmin` value rather than the helper result

### Requirement: One-time superadmin bootstrap

The initial superadmin SHALL be provisioned through the owner-configured bootstrap function `grant_bootstrap_superadmin` **once only**, and its completion SHALL be persisted across requests and restarts. Later logins as the configured subject SHALL NOT re-grant a revoked status, revoke appointed superadmins or overwrite an explicit administrative decision. Existing superadmins SHALL be preserved during migration. Recovery or rotation SHALL be an explicit owner action, never implicit on login.

#### Scenario: Previously bootstrapped subject is explicitly revoked

- **WHEN** an authorized superadmin revokes the previously bootstrapped subject while another superadmin remains
- **THEN** the revoked subject has no global access on its next request
- **AND** repeated logins do not silently grant its global status again

### Requirement: Multiple independent memberships per user

Users MAY have independent roles in multiple districts and congregations under one authenticated subject. Operations on one membership SHALL preserve others. Memberships SHALL be unique by `(user_sub, scope_type, scope_id)`, concurrency-safe and idempotent. Existing duplicates SHALL be consolidated without reducing the effective role or losing auditability.

#### Scenario: One user belongs to multiple congregations

- **WHEN** a user is assigned VIEWER in congregation A and PLANNER in congregation B
- **THEN** both memberships coexist under the same account
- **AND** the user can view A and plan in B without gaining planner rights in A

#### Scenario: Units in different districts

- **WHEN** a user receives authorized memberships in units belonging to different districts
- **THEN** the user can access each assigned unit according to its own membership
- **AND** units outside the user's effective scopes remain inaccessible

#### Scenario: Add another unit

- **WHEN** an authorized administrator adds a unit to an already assigned registered user
- **THEN** the new membership becomes available without another account or registration
- **AND** existing memberships are unchanged

#### Scenario: Remove one assignment

- **WHEN** an authorized administrator removes one of a user's memberships
- **THEN** that membership no longer grants access
- **AND** other memberships remain effective

#### Scenario: Assign the same scope again

- **WHEN** an authorized administrator assigns a new role for a scope already assigned to that user
- **THEN** the existing membership is updated without creating duplicates
- **AND** memberships in other scopes are unchanged

#### Scenario: Concurrent repeated assignment to the same scope
- **WHEN** two authorised requests concurrently assign a role to the same user, scope type and scope ID
- **THEN** only one membership row exists and other scopes remain unchanged

#### Scenario: Legacy memberships with different roles in one scope
- **WHEN** the migration sees VIEWER and PLANNER for the same user, scope type and scope ID
- **THEN** it retains one PLANNER membership and archives the redundant row without changing access to any other scope

### Requirement: Superadmins can appoint additional superadmins

A verified superadmin MAY grant or revoke global superadmin status to a securely linked registered user through explicit audited actions. Other roles MUST NOT grant this status, including through registration payloads. The last superadmin MUST NOT be revoked, including in concurrent operations. Revocation SHALL take effect on the next authorised request.

#### Scenario: Appoint another superadmin

- **WHEN** an existing superadmin grants superadmin status to a registered, securely linked user
- **THEN** that user becomes a superadmin and receives global access without additional memberships
- **AND** the appointment is audited

#### Scenario: District admin attempts appointment

- **WHEN** a district admin who is not a superadmin attempts to grant superadmin status
- **THEN** the request returns 403 Forbidden
- **AND** the target user's status remains unchanged

#### Scenario: Registration attempts self-promotion

- **WHEN** a non-superadmin attempts to set superadmin status through registration or membership assignment
- **THEN** no superadmin status is granted

#### Scenario: Revoke an additional superadmin
- **WHEN** an existing superadmin revokes another superadmin while at least one superadmin will remain
- **THEN** the target immediately loses global privileges and retains only independently authorised memberships
- **AND** the change is audited

#### Scenario: Cannot remove last superadmin
- **WHEN** an administrator attempts to revoke the sole remaining superadmin, including concurrent revocations
- **THEN** the operation is rejected atomically and a superadmin remains

#### Scenario: Role change while session is active
- **WHEN** a former superadmin uses a still-valid authenticated session after revocation and has no effective memberships
- **THEN** protected business endpoints return 403 and PostgreSQL RLS does not allow cross-tenant access

### Requirement: Administration exposes all assignments and global status

User administration SHALL display all memberships of a user within the administrator's authorized management scope, with unit and role, and SHALL show superadmin status to superadmins. The authenticated access context SHALL include all effective memberships and the current user's superadmin status so the frontend can expose all authorized units and actions.

#### Scenario: Superadmin inspects a user

- **WHEN** a superadmin opens a registered user's administration details
- **THEN** all of that user's unit assignments and their roles, and the global superadmin status, are visible

#### Scenario: Congregation-only member requests the access context

- **WHEN** an authenticated user whose memberships are all congregation-scoped requests the access context
- **THEN** the response lists those memberships with status ACTIVE
- **AND** the user is not treated as pending approval

#### Scenario: Client requests a superadmin's access context

- **WHEN** an authenticated superadmin with no memberships requests the access context
- **THEN** the response exposes superadmin status
- **AND** the frontend enables global unit selection and administrative actions
