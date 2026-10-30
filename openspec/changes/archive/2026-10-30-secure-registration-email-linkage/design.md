## Context
Direct `sub` binding during public registration and verified-email post-login linkage currently use different identity assurance levels. The former does not check email ownership.

## Decision
Require both `email_verified is True` and a case-insensitive exact match between the validated OIDC `email` claim and `RegistrationCreate.email`. Reject malformed or missing claims with 403 before DB writes. Keep anonymous submissions possible to preserve the separately approved email-based linking path. Keep invalid and missing-subject tokens at 401.

## Security trade-offs
- A provider that omits verified-email claims cannot use the authenticated direct-link path; the client must submit without a bearer token, and a verified-email login later links the approved registration. This fails closed.
- Email normalization uses trimming and casefolding to match the application's existing case-insensitive approved-registration lookup.

## Test strategy
- Unit tests cover mismatched email, false/string/missing verification, missing email, mixed-case match and no database writes after rejection.
- RLS PostgreSQL tests verify persisted rows are absent on denial and linked subjects are correct on success.
- CI coverage must remain >= 80%.
