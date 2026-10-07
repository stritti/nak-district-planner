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
Users with `is_superadmin` SHALL pass all role checks and SHALL be the only users allowed to create districts and to list cross-district resources without a district filter. The initial superadmin SHALL be granted through the bootstrap function `grant_bootstrap_superadmin` configured by subject.

#### Scenario: Cross-district listing
- **WHEN** a superadmin lists events without `district_id`
- **THEN** the request is allowed
