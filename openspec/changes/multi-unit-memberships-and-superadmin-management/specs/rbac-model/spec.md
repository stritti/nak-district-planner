## ADDED Requirements

### Requirement: Multiple independent memberships per user

A registered user SHALL be assignable to multiple districts and congregations under the same authenticated subject. Each membership SHALL retain its own scope and role. Memberships MAY include congregations in different districts and a combination of district and congregation scopes.

Adding a membership SHALL NOT replace existing memberships. Changing or removing one membership SHALL NOT modify others. Reassigning the same user and scope SHALL update the existing membership instead of creating duplicate memberships. Effective permissions of a non-superadmin SHALL be evaluated for the target scope using the existing role hierarchy and scope rules.

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

### Requirement: Superadmins can appoint additional superadmins

An authenticated existing superadmin SHALL be able to grant superadmin status to a registered user securely linked to an authenticated subject through user administration. This SHALL set the global is_superadmin status independently of unit memberships. Non-superadmins SHALL NOT grant superadmin status, including through registration or membership payloads. Successful appointments SHALL be recorded according to the existing audit rules.

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

### Requirement: Administration exposes all assignments and global status

User administration SHALL display all memberships of a user within the administrator's authorized management scope, with unit and role, and SHALL show superadmin status to superadmins. The authenticated access context SHALL include all effective memberships and the current user's superadmin status so the frontend can expose all authorized units and actions.

#### Scenario: Superadmin inspects a user

- **WHEN** a superadmin opens a registered user's administration details
- **THEN** all of that user's unit assignments and their roles, and the global superadmin status, are visible

#### Scenario: Client requests a superadmin's access context

- **WHEN** an authenticated superadmin with no memberships requests the access context
- **THEN** the response exposes superadmin status
- **AND** the frontend enables global unit selection and administrative actions

## MODIFIED Requirements

### Requirement: Superadmin

Users with is_superadmin SHALL have global access to all districts, congregations, business data and administrative functions, including management of registered users and appointment of further superadmins. They SHALL pass all role and scope checks without requiring memberships. This global access SHALL be applied consistently in API authorization, data access including row-level security, and frontend navigation and action visibility. Authentication and business validation rules SHALL remain applicable.

Superadmins SHALL be the only users allowed to create districts and to list cross-district resources without a district filter. The initial superadmin SHALL continue to be granted through the bootstrap function grant_bootstrap_superadmin configured by subject.

#### Scenario: Cross-district listing

- **WHEN** a superadmin lists events without district_id
- **THEN** the request is allowed and can include events across all districts

#### Scenario: Superadmin accesses an unassigned unit

- **WHEN** a superadmin without memberships accesses or administers a district or congregation
- **THEN** the action is authorized and the target data is available according to the requested operation

#### Scenario: Selected context does not limit authorization

- **WHEN** a superadmin has selected district A in the interface and requests an administrative action in district B
- **THEN** the selected context does not prevent authorization in district B
