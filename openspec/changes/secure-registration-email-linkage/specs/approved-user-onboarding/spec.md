## MODIFIED Requirements

### Requirement: Registration user linkage SHALL be secure
If a bearer token is provided in a self-registration request, the system MUST validate it before using its `sub` for linkage. The identity provider MUST attest to ownership of the registration email: `email_verified` SHALL be the Boolean `true` and the token `email` SHALL match the submitted registration email case-insensitively. The system MUST reject any authenticated request without these claims instead of binding it to the token subject.

#### Scenario: Valid token with verified matching email links registration
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
