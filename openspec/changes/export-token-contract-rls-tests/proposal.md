## Why

The hash-only export token contract migration is exercised by an owner database connection. An owner bypasses PostgreSQL RLS, so it does not prove tenant isolation or subscription behavior with the actual restricted application role. Addresses #628.

## What changes

- Extend the disposable database upgrade test to connect as a NOBYPASSRLS, non-owner `APP_DB_USER` after the contract migration.
- Assert permissions for PUBLIC, INTERNAL, PERSONAL, revoked, unknown and foreign-tenant tokens, both before/after upgrade as necessary to prove contract continuity.
- Compare PostgreSQL policy and SECURITY DEFINER definitions to the known-good tenant security snapshot; prohibit references to the dropped plaintext token column.
- Run deterministically in the existing integration CI with database and application credentials.

## Non-goals

- Change the token contract, reintroduce plaintext tokens or relax RLS.
- Depend on production or real subscribers during tests.

Issue: <https://github.com/stritti/nak-district-planner/issues/628>
