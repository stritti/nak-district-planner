## MODIFIED Requirements

### Requirement: Opaque token validation is scoped to this application
The backend MAY accept non-JWT (opaque) access tokens, but MUST validate them through RFC 7662 Introspection before authentication succeeds. The introspection response MUST contain `active` as the boolean `true`, a non-empty `sub` and a `client_id` exactly matching the configured OIDC client. A valid UserInfo response alone MUST NOT authenticate a token. Any present issuer, audience or authorized-party claim MUST also pass normal security claim checks. UserInfo MAY enrich a successfully introspected identity, but its subject MUST agree with the introspected subject; identity and security claim mismatches MUST fail closed.

#### Scenario: Valid UserInfo response without introspection
- **WHEN** an opaque token receives a successful UserInfo response but introspection is unavailable
- **THEN** authentication fails

#### Scenario: Introspection belongs to another client
- **WHEN** introspection reports an active token with a missing or different `client_id`
- **THEN** authentication fails before UserInfo is called

#### Scenario: Introspection active flag is not boolean true
- **WHEN** introspection returns `active: "false"` or any other non-boolean-true value
- **THEN** authentication fails

#### Scenario: Resource audience mismatches but authorized party matches
- **WHEN** an opaque introspection result contains an `aud` excluding this application
- **AND** `azp` equals the configured client
- **THEN** authentication fails because `azp` does not replace the resource audience

#### Scenario: UserInfo returns a mismatching security claim or subject
- **WHEN** a client-bound, active opaque token is confirmed by introspection
- **AND** UserInfo returns a different subject or a mismatching issuer, client or audience claim
- **THEN** authentication fails even though introspection was successful

#### Scenario: Valid client-bound introspection with optional UserInfo
- **WHEN** introspection reports a matching client and an active token with a subject
- **THEN** authentication succeeds whether UserInfo supplies matching profile data or is unavailable
- **AND** introspection remains authoritative for security claims
