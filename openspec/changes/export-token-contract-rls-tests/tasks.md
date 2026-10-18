## 1. Restricted runtime-role test fixtures
- [ ] 1.1 Extend disposable migration fixture with NOBYPASSRLS app-role access.
- [ ] 1.2 Seed paired tenants and PUBLIC, INTERNAL and personal subscriptions.

## 2. Authorization tests
- [ ] 2.1 Assert valid subscription scopes and cross-tenant denial.
- [ ] 2.2 Assert revoked/unknown credentials and missing subject fail closed.
- [ ] 2.3 Snapshot active RLS policies and SECURITY DEFINER functions after contract upgrade.

## 3. CI and completion
- [ ] 3.1 Run non-owner tests with CI role configuration; fail expected missing prerequisites.
- [ ] 3.2 Execute whole integration suite, migration roundtrip checks and coverage >=80%.
- [ ] 3.3 Independent review and production migration contract verification.
