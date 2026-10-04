## MODIFIED Requirements

### Requirement: JWT validation fails closed
The backend SHALL classify compact three-segment tokens as JWT-like and SHALL validate them exclusively through cryptographic JWT validation. A JWT validation error MUST NOT trigger UserInfo or Introspection fallback.

#### Scenario: JWT has invalid audience
- **WHEN** a JWT-like access token has an audience that does not match the configured client/audience
- **THEN** authentication fails
- **AND** UserInfo and Introspection are not called as fallback validators

#### Scenario: JWT is expired or has invalid issuer/signature
- **WHEN** cryptographic JWT validation fails for expiration, issuer, signing key or signature reasons
- **THEN** authentication fails closed
- **AND** the token is not reinterpreted as opaque

### Requirement: Opaque token validation is scoped to this application
The backend MAY validate non-JWT access tokens through UserInfo and RFC 7662 Introspection. Security-relevant issuer, client and audience claims returned by those endpoints SHALL match the configured application whenever such claims are present.

#### Scenario: Introspection belongs to another client
- **WHEN** introspection returns an active token with a different `client_id` or audience
- **THEN** authentication fails

#### Scenario: Opaque UserInfo response is valid
- **WHEN** a non-JWT access token is accepted by UserInfo and contains a subject
- **AND** all security-relevant claims that are present match the configured application
- **THEN** authentication succeeds