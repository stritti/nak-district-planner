# approved-user-onboarding Specification

## Purpose

Separates self-registration from access activation: a district administrator approves registrations with an explicit role and scope, optionally provisioning the user in the IdP.

## Requirements

### Requirement: Registration approval SHALL activate user access explicitly

The system SHALL treat self-registration and access activation as separate steps. A registered non-superadmin user MUST NOT gain access to protected business endpoints until an authorized administrator approves the registration and assigns an authorization scope.

#### Scenario: Registered but not approved user logs in

- **WHEN** a non-superadmin user authenticates successfully via OIDC but has no approved access assignment
- **THEN** protected business endpoints return 403 Forbidden
- **AND** the response indicates that approval is pending

#### Scenario: District admin approves registration

- **WHEN** a district admin approves a pending registration within their authorized scope
- **THEN** the registration status changes to APPROVED
- **AND** approval metadata (approved_by_sub, approved_at) is stored

### Requirement: Superadmin status SHALL stand in for approval while it lasts

A user explicitly granted superadmin status by an existing superadmin SHALL have global access without an approval-created membership. If that status is later revoked and no approved effective membership exists, protected business access SHALL revert to 403 and the pending client state, regardless of any earlier registration state.

#### Scenario: Appointed superadmin has no memberships

- **WHEN** a registered user securely linked to an authenticated subject has been appointed superadmin by an existing superadmin
- **THEN** protected business endpoints allow global access without requiring a membership
- **AND** the frontend does not treat the user as pending approval solely because their membership list is empty

#### Scenario: Revoked superadmin without memberships

- **WHEN** the superadmin status of a user without approved memberships is revoked
- **THEN** protected business endpoints return 403 on the next request
- **AND** the access context reports the pending state again


### Requirement: Approval SHALL include role and scope assignment
The system SHALL require explicit authorization assignment during approval. Approval payload MUST include `role`, `scope_type`, and `scope_id`.

#### Scenario: Approval request missing assignment fields
- **WHEN** admin submits approval without one or more required assignment fields
- **THEN** system rejects the request with `422 Unprocessable Entity`

#### Scenario: Approval creates effective membership
- **WHEN** admin approves with valid `role`, `scope_type`, and `scope_id`
- **THEN** system creates or updates a membership for the approved user
- **AND** future authorization checks use that membership for access decisions

### Requirement: Approval SHALL support optional IDP provisioning
When enabled by configuration, the system SHALL notify a provisioning endpoint at approval time so the user can be invited/created in the external IDP.

#### Scenario: Provisioning enabled and endpoint succeeds
- **WHEN** a registration is approved and provisioning is enabled
- **THEN** system calls the configured provisioning endpoint with registration and scope metadata
- **AND** stores provisioning status on the registration

#### Scenario: Provisioning endpoint fails
- **WHEN** provisioning is enabled and endpoint call fails
- **THEN** approval remains successful for internal authorization state
- **AND** registration stores provisioning error details for operators

### Requirement: Registration user linkage SHALL be secure
If a bearer token is provided in a self-registration request, the system MUST validate it before using its `sub` for linkage. The identity provider MUST attest to ownership of the registration email: `email_verified` SHALL be the Boolean `true` and the token `email` SHALL match the submitted registration email case-insensitively. The system MUST reject any authenticated request without these claims instead of binding it to the token subject.

#### Scenario: Valid token links registration to subject
- **WHEN** registration includes a valid bearer token with a nonempty `sub`, a matching `email` and Boolean `email_verified=true`
- **THEN** system stores the token's `sub` as registration `user_sub`

#### Scenario: Invalid token is rejected
- **WHEN** registration request includes an invalid or expired bearer token or one missing a subject
- **THEN** system rejects the request with `401 Unauthorized`

#### Scenario: Registration without token remains possible
- **WHEN** registration request is sent without a bearer token
- **THEN** system accepts registration as pending
- **AND** `user_sub` remains unset until later secure linkage

#### Scenario: Subject cannot be linked to a different email
- **WHEN** a valid token carries an email different from the submitted registration email
- **THEN** system returns `403 Forbidden` without persisting the registration or identity link

#### Scenario: Only explicitly verified email may be linked
- **WHEN** a valid token has no `email`, no `email_verified`, `email_verified=false` or a non-Boolean `email_verified`
- **THEN** system returns `403 Forbidden` without persisting the registration or identity link

### Requirement: The backend SHALL hold no IdP administration credential
The backend MUST NOT create, modify or invite users in Keycloak and MUST NOT be configured with a Keycloak Admin API credential. When the former Keycloak provisioning provider is still configured, the application SHALL refuse to start.

#### Scenario: Keycloak provider still configured
- **WHEN** the application starts with `IDP_PROVISIONING_PROVIDER=keycloak` and provisioning enabled
- **THEN** startup is refused with a configuration error that names the setting and points to the upgrade note

#### Scenario: Approval without provisioning
- **WHEN** a district admin approves a registration and no provisioning provider is configured
- **THEN** the registration is approved and no request is sent to the IdP

#### Scenario: Provisioning client removed by setup
- **WHEN** the realm setup script runs against a realm that contains the client `nak-planner-provisioning`
- **THEN** the script deletes that client and creates no client with a service account

#### Scenario: Provisioning client inspection returns an invalid response
- **WHEN** the realm setup receives an unexpected shape from the Keycloak client-list API
- **THEN** setup fails rather than treating the former provisioning client as absent

### Requirement: User accounts SHALL be created by self-registration with a verified email
The documented realm setup SHALL allow users to register themselves in the application realm only with email verification and the email address as username. Access to protected business endpoints SHALL still require an approved registration linked by `sub` or by a verified email claim.

#### Scenario: Realm allows verified self-registration
- **WHEN** the realm setup script runs
- **THEN** the realm has `registrationAllowed`, `verifyEmail` and `registrationEmailAsUsername` enabled

#### Scenario: Self-registered account without approval
- **WHEN** a user registers in Keycloak, verifies the email and logs in without an approved registration
- **THEN** protected business endpoints return `403 Forbidden` indicating that approval is pending

#### Scenario: Approved registration linked on first login
- **WHEN** a registration for an email is approved and the user later logs in with a token whose `email` matches and `email_verified` is `true`
- **THEN** the user receives the approved membership

#### Scenario: Registration page offers account creation
- **WHEN** an unauthenticated user submits the registration form
- **THEN** the page offers to create an account, which starts the OIDC login with `prompt=create`, and states that the account email must match the registration email

#### Scenario: Authenticated user registers
- **WHEN** an authenticated user submits the registration form
- **THEN** the request carries the user's access token and the registration stores the token's `sub`

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

### Requirement: Administrators can manage additional unit assignments

Superadmins SHALL manage district and congregation memberships of securely linked users across all units. Other administrators MAY manage only authorised scopes and roles no higher than their own. A congregation admin MUST NOT create district roles. Managing one assignment SHALL preserve the existing account and other assignments.

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
