## ADDED Requirements

### Requirement: Registration auto-linking SHALL require a verified email claim
The system SHALL bind an approved, unlinked registration to the authenticated user only when the token carries an `email` claim and the `email_verified` claim is the boolean `true`. Any other value, including the string `"true"` or a missing claim, MUST be treated as unverified.

#### Scenario: Verified email links the registration
- **WHEN** a user logs in with `email` matching exactly one approved unlinked registration and `email_verified` is boolean `true`
- **THEN** the registration is linked to the user's subject and the assigned membership becomes effective

#### Scenario: Missing or false email_verified does not link
- **WHEN** a user logs in with a matching `email` but `email_verified` is missing, `false` or a non-boolean value
- **THEN** no registration is linked and no membership is granted

#### Scenario: Username fallback does not link
- **WHEN** the token has no `email` claim but `preferred_username` contains an email address matching an approved registration
- **THEN** the username is used for display only and no registration is linked

### Requirement: IdP provisioning SHALL bind only to verified IdP accounts
The Keycloak provisioner SHALL return an existing account's id as the registration's subject only when that account has `emailVerified=true`. Otherwise the registration MUST stay unlinked and the status MUST be `EXISTING_UNVERIFIED` (or `EXISTING_UNVERIFIED_INVITED` when an invite was sent).

#### Scenario: Existing verified account is bound
- **WHEN** approval provisioning finds an existing Keycloak account with `emailVerified=true`
- **THEN** the account id is returned as `user_sub` and the membership is created

#### Scenario: Existing unverified account is not bound
- **WHEN** approval provisioning finds an existing Keycloak account without `emailVerified=true` (including after a 409 conflict on create)
- **THEN** no `user_sub` is returned and the status is `EXISTING_UNVERIFIED` or `EXISTING_UNVERIFIED_INVITED`
