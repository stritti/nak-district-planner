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
| | `/api/v1/auth/oidc/token` | POST | 🔓 Public | AUDIT | RL |
| | `/api/v1/auth/me` | GET | 🔐 Auth | – | RL |
| | `/api/v1/auth/access` | GET | 🔐 Auth + Membership-Check | – | RL |
| **calendar_integrations** | `/api/v1/calendar-integrations` | GET | SUPERADMIN / R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | – | RL |
| | | POST | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | RL |
| | `/{integration_id}` | PATCH | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | RL |
| | | DELETE | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | RL |
| | `/{integration_id}/sync` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| **districts** | `/api/v1/districts` | GET | R(VIEWER) | – | RL |
| | | POST | SUPERADMIN | AUDIT | RL |
| | `/{district_id}` | PATCH | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{district_id}/congregations` | GET | R(VIEWER) | – | RL |
| | | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{district_id}/congregations/{congregation_id}` | PATCH | R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | AUDIT | RL |
| | `/{district_id}/groups` | GET | R(VIEWER) | – | RL |
| | | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{district_id}/groups/{group_id}` | PATCH | R(DISTRICT_ADMIN) | AUDIT | RL |
| | | DELETE | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{id}/matrix` | GET | R(VIEWER) | – | RL |
| | `/{id}/matrix/generate-drafts` | POST | R(PLANNER) | AUDIT | RL |
| | `/{id}/leaders` | GET | R(VIEWER) | – | RL |
| | | POST | R(PLANNER) | AUDIT | RL |
| | `/{id}/leaders/{leader_id}` | PATCH | R(PLANNER) | AUDIT | RL |
| | | DELETE | R(PLANNER) | AUDIT | RL |
| | `/{id}/leaders/link-self` | GET | R(VIEWER) | – | RL |
| | | POST | R(VIEWER) | AUDIT | RL |
| | | DELETE | R(VIEWER) | AUDIT | RL |
| | `/{id}/planning-series` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | | GET | R(VIEWER) | – | RL |
| | | PATCH | R(DISTRICT_ADMIN) | AUDIT | RL |
| | | DELETE | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{id}/generate-planning-series` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{district_id}/feiertage/states` | GET | 🔐 Auth | – | RL |
| | `/{district_id}/feiertage` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| **events_compat** | `/api/v1/events?district_id=...` | GET | R(VIEWER) | – | RL |
| | `/api/v1/events/{event_id}` | PATCH | R(PLANNER) | AUDIT | RL |
| | `/api/v1/events/bulk-approval-status` | POST | R(PLANNER) | AUDIT | RL |
| **export** | `/api/v1/export-tokens` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/api/v1/export-tokens` | GET | SUPERADMIN / R(DISTRICT_ADMIN) | – | RL |
| | `/api/v1/export-tokens/{token_id}` | DELETE | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/api/v1/export/{token}/calendar.ics` | GET | 🔓 Public (Token-basiert) | – | RL |
| **invitations** | `/api/v1/events/{event_id}/invitations` | GET | R(VIEWER) | – | RL |
| | | POST | R(PLANNER) | AUDIT | RL |
| | `/api/v1/invitations/{invitation_id}` | DELETE | R(PLANNER) | AUDIT | RL |
| | `/api/v1/invitations/overwrite-requests` | GET | R(VIEWER) | – | RL |
| | `/api/v1/invitations/overwrite-requests/{request_id}/decision` | POST | R(PLANNER) | AUDIT | RL |
| **leaders** | `/api/v1/districts/{district_id}/leaders/...` | – | – | – | – |
| | (siehe districts oben — alle leaders-Router sind dort sub-routet) | | | | |
| **notifications** | `/api/v1/notifications/{district_id}` | GET | R(VIEWER) | – | RL |
| | `/api/v1/notifications/{district_id}/unread-count` | GET | R(VIEWER) | – | RL |
| | `/api/v1/notifications/{notification_id}/read` | POST | R(VIEWER) | AUDIT | RL |
| | `/api/v1/notifications/{district_id}/read-all` | POST | R(VIEWER) | AUDIT | RL |
| **planning_series** | `/api/v1/planning-series` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{series_id}` | GET | R(VIEWER) | – | RL |
| | | PATCH | R(DISTRICT_ADMIN) | AUDIT | RL |
| | | DELETE | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{series_id}/generate-slots` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/districts/{district_id}/generate-slots` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/generate-all-slots` | POST | SUPERADMIN | AUDIT | RL |
| **registrations** | `/api/v1/public/districts` | GET | 🔓 Public | – | RL |
| | `/api/v1/public/districts/{district_id}/congregations` | GET | 🔓 Public | – | RL |
| | `/api/v1/districts/{district_id}/registrations` | POST | 🔓 Public | AUDIT | RL |
| | | GET | R(DISTRICT_ADMIN) | – | RL |
| | `/{registration_id}/approve` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{registration_id}/reject` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{registration_id}` | DELETE | R(DISTRICT_ADMIN) | AUDIT | RL |
| **registrations_overview** | `/api/v1/registrations/pending-overview` | GET | R(DISTRICT_ADMIN) / SUPERADMIN | – | RL |
| **service_assignments** | `/api/v1/events/{event_id}/assignments` | GET | R(VIEWER) | – | RL |
| | | POST | R(PLANNER) | AUDIT | RL |
| | `/{id}` | PUT | R(PLANNER) | AUDIT | RL |
| | | DELETE | R(PLANNER) | AUDIT | RL |
| **system** | `/api/v1/system/version` | GET | SUPERADMIN / R(DISTRICT_ADMIN) / R(CONGREGATION_ADMIN) | – | RL |
| | `/api/v1/system/update` | POST | SUPERADMIN | AUDIT | RL |
| **health** | `/api/health` | GET/HEAD/OPTIONS | 🔓 Public | – | – |

## Anmerkungen

1. **Self-Link-Endpunkte** (`leaders/link-self`) nutzen `R(VIEWER)` auf Bezirksebene
   (mit optionaler Gemeinde-Einschränkung), nicht nur `🔐 Auth`. Das ist bewusst so designed,
   da der Self-Link-Flow die Voraussetzung für die erste Rollenvergabe ist.
2. **Export-Endpunkte** sind token-basiert öffentlich, aber durch pfadspezifisches Rate-Limiting
   (`60 req/min`) geschützt.
3. **Registrierungs-Endpunkte**: Der öffentliche POST `/api/v1/districts/{district_id}/registrations`
   prüft nur die Bezirks-Existenz und optional ein Bearer-Token; ein CAPTCHA wird aktuell nicht erzwungen.
4. Der DRY-Refactor (PR-4) hat alle `try/except PermissionError`-Pattern in Routern durch
   `require_role_in_*()`-Aufrufe ersetzt. Eine CI-Lint-Regel (`scripts/check_rbac_guard_pattern.py`)
   verhindert neue Vorkommen des alten Patterns.
5. **Globales Rate-Limiting**: Alle Routen außer `/api/health` unterliegen dem globalen
   `RateLimitMiddleware` (Standard: 200 req/min für anonyme, 400 req/min für authentifizierte Nutzer
   via `default_limit=200` und `authenticated_multiplier=2.0` in `main.py:131-134`).

## Siehe auch

- `docs/roles.md` — Rollenmodell und Berechtigungsmatrix
- `docs/code-review-2026-07.md` — Code-Review mit detaillierten Findings
- `docs/code-review-2026-07-action-plan.md` — Aktionsplan mit Status
- `services/backend/scripts/check_rbac_guard_pattern.py` — CI-Lint-Regel für RBAC-Guard-Pattern
