## ADDED Requirements

### Requirement: OIDC Configuration for Keycloak
When deploying NAK District Planner with Keycloak as the OIDC provider, the system SHALL support standard OIDC discovery and standard client configuration.

#### Scenario: Keycloak OIDC Application Setup
- **WHEN** Keycloak realm is created with client `nak-planner-api` configured for OIDC
- **THEN** discovery endpoint is `https://auth.5tritti.de/realms/{REALM_NAME}/.well-known/openid-configuration`
- **AND** client configuration includes `redirect_uris`, `logout_redirect_uris`, enabled scopes: `openid`, `profile`, `email`

#### Scenario: Keycloak Token Exchange
- **WHEN** frontend sends authorization code to Keycloak's `token_endpoint`
- **THEN** Keycloak returns ID token and access token with standard OIDC claims

#### Scenario: Keycloak JWKS Validation
- **WHEN** backend validates token from Keycloak
- **THEN** fetches JWKS from `https://auth.5tritti.de/realms/{REALM_NAME}/protocol/openid-connect/certs`
- **AND** validates signature using `RS256` algorithm (Keycloak default)

#### Scenario: Keycloak Token Refresh
- **WHEN** frontend needs to refresh access token
- **THEN** sends refresh token to Keycloak's `token_endpoint` with `grant_type=refresh_token`

### Requirement: OIDC Configuration for Authentik
When deploying NAK District Planner with Authentik as the OIDC provider, the system SHALL support standard OIDC discovery and standard client configuration.

#### Scenario: Authentik OIDC Application Setup
- **WHEN** Authentik application is created with OIDC protocol for `nak-planner-api`
- **THEN** discovery endpoint is `https://authentik.internal/application/o/{APP_SLUG}/.well-known/openid-configuration`
- **AND** client configuration includes `redirect_uris`, logout redirect URIs, enabled scopes: `openid`, `profile`, `email`

#### Scenario: Authentik Token Exchange
- **WHEN** frontend sends authorization code to Authentik's `token_endpoint`
- **THEN** Authentik returns ID token and access token with standard OIDC claims

#### Scenario: Authentik JWKS Validation
- **WHEN** backend validates token from Authentik
- **THEN** fetches JWKS from Authentik's discovery document `jwks_uri`
- **AND** validates signature using provider's algorithm (typically `RS256`)

#### Scenario: Authentik Token Refresh
- **WHEN** frontend needs to refresh access token
- **THEN** sends refresh token to Authentik's `token_endpoint` with `grant_type=refresh_token`

### Requirement: IDP-Agnostic Configuration Template
The system SHALL provide clear setup documentation for both Keycloak and Authentik that demonstrates how to configure identical OIDC settings.

#### Scenario: Documentation structure
- **WHEN** developer reads setup guide
- **THEN** finds parallel sections for Keycloak and Authentik showing:
  - Required OIDC client configuration (scopes, redirect URIs)
  - Where to find discovery URL in each IDP
  - How to obtain `CLIENT_ID`, `CLIENT_SECRET`
  - Example `.env` file for both providers

#### Scenario: ENV variable mapping for both IDPs
- **WHEN** operator configures backend with `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`
- **THEN** same environment variables work for both Keycloak and Authentik
- **AND** documentation shows example values for each provider

#### Scenario: Token validation is identical for both IDPs
- **WHEN** documentation explains JWT validation
- **THEN** describes standard OIDC claims and JWKS validation
- **AND** notes that validation logic is provider-agnostic

### Requirement: OIDC Deployment Guide
The system SHALL provide Docker Compose templates and deployment guides for both Keycloak and Authentik in a `idp-deploy/` directory.

#### Scenario: Keycloak subdirectory with docker-compose
- **WHEN** operator navigates to `idp-deploy/keycloak/`
- **THEN** finds `docker-compose.yml` for Keycloak 26.5.6 with PostgreSQL and Traefik integration
- **AND** includes `SETUP.md` with Keycloak-specific realm + client creation

#### Scenario: Authentik subdirectory with docker-compose
- **WHEN** operator navigates to `idp-deploy/authentik/`
- **THEN** finds `docker-compose.yml` for Authentik with PostgreSQL
- **AND** includes `SETUP.md` with Authentik-specific application + OAuth2 client creation

#### Scenario: Identical ENV variable names across IDPs
- **WHEN** operator runs deployment script for either IDP
- **THEN** script outputs `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` (not provider-specific names)
- **AND** same ENV variables can be used in `nak-district-planner/.env`

