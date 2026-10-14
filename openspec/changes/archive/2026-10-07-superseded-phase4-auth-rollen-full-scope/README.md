# Archived: phase4-auth-rollen (Full Scope)

Diese Change war zu groß für einen Schritt. Sie wurde gesplittet in:

## Phase 4a: JWT Auth (MVP - gerade eben)
`openspec/changes/phase4a-jwt-auth-minimal/`

- JWT-Validierung via Keycloak JWKS
- User auto-create on first login
- Login/Logout Flow
- Bearer Token Authentication

**Ziel:** 2-3 Tage. Genug für Deployment.

## Phase 5: RBAC + User Management (später)
*(noch nicht erstellt)*

- Rollen-Modell (system_admin, district_admin, planner, viewer)
- `require_role(...)` Guards auf Routes
- User Management API (add/remove users, assign roles)
- Audit Logging
- Rollen-Cache (Redis)

---

## Warum aufgesplittet?

Phase4-auth-rollen (34 Tasks) versuchte alles auf einmal zu machen:
- Keycloak-Infrastruktur ✓ (gehört zu MVP)
- JWT-Validierung ✓ (gehört zu MVP)
- **Rollen-Modell** ✗ (deferrable)
- **Role-based Guards** ✗ (deferrable)
- **User-Management-UI** ✗ (deferrable)
- **Audit-Logging** ✗ (gehört zu `introduce-non-functional-baseline`)

**MVP-Auth** (4a) brauchst du um zu deployen. **RBAC** (5) brauchst du für Multi-Tenant-Governance.

Stufenweise → schneller zum Deployment → stabilere Iterationen.

---

Falls du jemals zurück zum Original-Design willst, ist es hier archiviert.
