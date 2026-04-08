## 1. Domain and Data Model

- [ ] 1.1 Extend registration domain model with approval assignment fields (`assigned_role`, `assigned_scope_type`, `assigned_scope_id`, `approved_by_sub`, `approved_at`)
- [ ] 1.2 Create and apply migration for new registration approval/assignment columns
- [ ] 1.3 Ensure membership persistence supports idempotent upsert by (`user_sub`, `scope_type`, `scope_id`)

## 2. Registration and Approval API

- [ ] 2.1 Update self-registration endpoint to validate optional bearer token before setting `user_sub`
- [ ] 2.2 Extend approval schema and endpoint to require `role`, `scope_type`, and `scope_id`
- [ ] 2.3 Implement membership creation/update during approval using assigned role and scope
- [ ] 2.4 Persist approval audit metadata (`approved_by_sub`, `approved_at`) in approval flow
- [ ] 2.5 Define and implement secure post-login linking strategy for approved registrations without `user_sub`

## 3. Authorization Enforcement

- [ ] 3.1 Add a reusable access guard that denies protected endpoint access when user has no memberships (except superadmin)
- [ ] 3.2 Apply guard consistently to protected business routers
- [ ] 3.3 Verify district/congregation checks continue to enforce role hierarchy within matching scope only

## 4. Frontend and UX Integration

- [ ] 4.1 Add authenticated access-context endpoint response model (memberships for UI)
- [ ] 4.2 Update admin approval UI to select role and scope during release decision
- [ ] 4.3 Add authenticated pending-approval UX state ("Freigabe ausstehend") when membership list is empty

## 5. Tests and Documentation

- [ ] 5.1 Add unit tests for token validation in registration and approval-driven membership creation
- [ ] 5.2 Add integration tests for access denial before approval and scoped access after approval
- [ ] 5.3 Add E2E test for registration -> approval -> login -> scoped data access
- [ ] 5.4 Update operational docs with approval workflow, scope assignment rules, and rollback guidance
- [ ] 5.5 Add migration/backfill runbook for existing users without memberships before guard rollout
