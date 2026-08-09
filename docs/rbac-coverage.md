# RBAC-Coverage: Router × Endpoint × Erforderliche Rolle

> **Stand:** Juli 2026 — basierend auf statischer Analyse (`docs/code-review-2026-07.md` Finding M-4)
> und dem abgeschlossenen DRY-Refactor (PR-4).
> **Sinn:** Verhindert erneutes manuelles Nachzählen bei künftigen Reviews.

Legende:
- `🔓 Public` — kein Auth/keine Rolle erforderlich (OIDC-Discovery, Health)
- `🔐 Auth` — gültiges JWT erforderlich, aber keine spezifische Rollenprüfung
- `R(VIEWER)` — `require_role_in_district(auth, Role.VIEWER, district_id)`
- `R(PLANNER)` — `require_role_in_district(auth, Role.PLANNER, district_id)`
- `R(DISTRICT_ADMIN)` — `require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)`
- `R(CONGREGATION_ADMIN)` — `require_role_in_congregation(auth, Role.CONGREGATION_ADMIN, congregation_id)`
- `AUDIT` — über AuditMiddleware protokolliert (POST/PUT/DELETE)
- `RL` — Rate-Limiting aktiv

---

## Routers

| Router | Endpoint | Methode | Guard | Audit | RL |
|---|---|---|---|---|---|
| **auth** | `/api/v1/auth/oidc/discovery` | GET | 🔓 Public | – | RL |
| | `/api/v1/auth/oidc/token` | POST | 🔓 Public | – | RL |
| | `/api/v1/auth/me` | GET | 🔐 Auth | – | – |
| | `/api/v1/auth/access` | GET | 🔐 Auth + Membership-Check | – | – |
| **calendar_integrations** | `/api/v1/calendar-integrations` | GET | SUPERADMIN / R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | – | – |
| | | POST | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | – |
| | `/{id}` | GET | R(VIEWER) | – | – |
| | | PUT | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | – |
| | | DELETE | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | – |
| | `/{id}/sync` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| **districts** | `/api/v1/districts` | GET | R(VIEWER) | – | – |
| | | POST | SUPERADMIN | AUDIT | – |
| | `/{id}` | GET | R(VIEWER) | – | – |
| | | PUT | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/{id}/events` | GET | R(VIEWER) | – | RL |
| | `/{id}/matrix` | GET | R(VIEWER) | – | – |
| | `/{id}/leaders` | GET | R(VIEWER) | – | – |
| | | POST | R(PLANNER) | AUDIT | – |
| | `/{id}/leaders/{leader_id}` | GET | R(VIEWER) | – | – |
| | | PUT | R(PLANNER) | AUDIT | – |
| | | DELETE | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/{id}/leaders/link-self` | GET | 🔐 Auth | – | – |
| | | POST | 🔐 Auth | AUDIT | – |
| | | DELETE | 🔐 Auth | AUDIT | – |
| | `/{id}/planning-series` | CRUD | R(PLANNER) | AUDIT | – |
| | `/{id}/feiertage/import` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| **events_compat** | `/api/v1/events` | GET | R(VIEWER) | – | RL |
| | `/api/v1/events/{event_id}` | PATCH | R(PLANNER) | AUDIT | – |
| | `/api/v1/events/bulk-approval-status` | POST | R(PLANNER) | AUDIT | – |
| **export** | `/api/v1/export/{token}/calendar.ics` | GET | 🔓 Public (Token-basiert) | – | RL |
| **invitations** | `/api/v1/invitations` | POST | R(PLANNER) | AUDIT | – |
| | `/{id}/respond` | POST | 🔐 Auth | AUDIT | – |
| **leaders** | `/api/v1/districts/{district_id}/leaders/...` | – | – | – | – |
| | (siehe districts oben — alle leaders-Router sind dort sub-routet) | | | | |
| **notifications** | `/api/v1/notifications` | GET | 🔐 Auth | – | – |
| | `/{id}/read` | POST | 🔐 Auth | AUDIT | – |
| **planning_series** | `/api/v1/planning-series` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/{series_id}` | GET | R(VIEWER) | – | – |
| | | PATCH | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/{series_id}/generate-slots` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/districts/{district_id}/generate-slots` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/generate-all-slots` | POST | SUPERADMIN | AUDIT | – |
| **registrations** | `/api/v1/registrations` (public) | POST | 🔓 Public | – | – |
| | `/api/v1/registrations/pending` | GET | R(DISTRICT_ADMIN) | – | – |
| | `/{id}/approve` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| | `/{id}/reject` | POST | R(DISTRICT_ADMIN) | AUDIT | – |
| **service_assignments** | `/api/v1/events/{event_id}/assignments` | GET | R(VIEWER) | – | – |
| | | POST | R(PLANNER) | AUDIT | – |
| | `/{id}` | PUT | R(PLANNER) | AUDIT | – |
| | | DELETE | R(PLANNER) | AUDIT | – |
| **system** | `/api/v1/system/version` | GET | R(DISTRICT_ADMIN) | – | – |
| | `/api/v1/system/update` | POST | SUPERADMIN | AUDIT | – |
| **health** | `/api/health` | GET/HEAD/OPTIONS | 🔓 Public | – | – |

## Anmerkungen

1. **Self-Link-Endpunkte** (`leaders/link-self`) nutzen nur `🔐 Auth` (gültiges JWT) ohne
   zusätzliche Rollenprüfung — dies ist bewusst so designed, da der Self-Link-Flow die
   Voraussetzung für die erste Rollenvergabe ist. Die RBAC-Lücke (B-1) wurde durch
   zusätzliche Validierung im Service-Layer geschlossen (PR [#209](https://github.com/stritti/nak-district-planner/pull/209)).
2. **Export-Endpunkte** sind token-basiert öffentlich, aber durch pfadspezifisches Rate-Limiting
   (`60 req/min`) geschützt.
3. **Registrierungs-Endpunkte** (POST) sind öffentlich, erfordern aber ein gültiges CAPTCHA
   (sofern konfiguriert).
4. Der DRY-Refactor (PR-4) hat alle `try/except PermissionError`-Pattern in Routern durch
   `require_role_in_*()`-Aufrufe ersetzt. Eine CI-Lint-Regel (`scripts/check_rbac_guard_pattern.py`)
   verhindert neue Vorkommen des alten Patterns.

## Siehe auch

- `docs/roles.md` — Rollenmodell und Berechtigungsmatrix
- `docs/code-review-2026-07.md` — Code-Review mit detaillierten Findings
- `docs/code-review-2026-07-action-plan.md` — Aktionsplan mit Status
- `services/backend/scripts/check_rbac_guard_pattern.py` — CI-Lint-Regel für RBAC-Guard-Pattern
