# Require client-bound introspection for opaque OIDC tokens

## Why

Issue #471 identifies an authorization boundary error: successful OIDC UserInfo alone does not establish that an opaque access token was issued to the planner application. Tokens from unrelated clients in the same issuer could be accepted.

## What Changes

- Require successful RFC 7662 introspection with an exact matching `client_id` before an opaque access token is accepted.
- Reject non-boolean `active`, absent client binding, conflicting subject or security claims.
- Use UserInfo only for optional profile enrichment; keep JWT verification unchanged.
- Add negative regression coverage and update the OIDC baseline contract.

## Impact

An identity provider supporting opaque access tokens must expose an authenticated introspection endpoint that returns `client_id`. Providers not meeting this contract fail closed; production Keycloak JWT access tokens remain unaffected.
