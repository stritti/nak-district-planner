## 1. Restricted runtime-role test fixtures
- [x] 1.1 Extend disposable migration fixture with NOBYPASSRLS app-role access.
- [x] 1.2 Seed paired tenants and PUBLIC, INTERNAL and personal subscriptions.

## 2. Authorization tests
- [x] 2.1 Assert valid subscription scopes and cross-tenant denial.
- [x] 2.2 Assert revoked/unknown credentials and missing subject fail closed.
- [x] 2.3 Inspect active RLS policies and SECURITY DEFINER functions after contract upgrade (no `export_tokens.token` reference, `token_hash` in use).

## 3. CI and completion
- [x] 3.1 Run non-owner tests with CI role configuration; fail expected missing prerequisites.
- [x] 3.2 Execute whole integration suite, migration roundtrip checks and coverage >=80%.
- [x] 3.3a Independent review.
- [ ] 3.3b Production migration contract verification (operator).
