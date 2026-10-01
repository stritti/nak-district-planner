# RBAC-Coverage: Router × Endpoint × Erforderliche Rolle

> **Stand:** September 2026 — die fachliche Rollentabelle ist kuratiert; das
> [Endpoint-Inventar](#generiertes-endpoint-inventar) am Ende wird aus dem Code generiert.
> **Sinn:** Verhindert erneutes manuelles Nachzählen bei künftigen Reviews.
>
> **Automatisierte Absicherung:** `services/backend/tests/unit/test_permission_coverage.py`
> schlägt fehl, wenn eine Route ohne `get_current_user`-Abhängigkeit oder ohne RBAC-Guard
> (`require_role_in_district`, `require_superadmin`, `assert_has_role_in_*`, `has_role_in_*`,
> `get_*_where_user_has_role`, `is_superadmin`) hinzukommt, eine Route doppelt registriert ist
> oder das generierte Inventar unten veraltet ist. Bewusste Ausnahmen stehen mit Begründung in
> `PUBLIC_ENDPOINTS` bzw. `AUTHENTICATED_WITHOUT_ROLE` im Test.

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
| **external_candidates** | `/api/v1/external-candidates?district_id=...` | GET | R(DISTRICT_ADMIN) | – | RL |
| | `/{candidate_id}/accept` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{candidate_id}/dismiss` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| **districts** | `/api/v1/districts` | GET | 🔐 Auth + sichtbare Bezirke gefiltert | – | RL |
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
| | `/{id}/generate-planning-series` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| | `/{id}/leader-unavailabilities` | GET | R(VIEWER) | – | RL |
| | | POST | R(PLANNER) | AUDIT | RL |
| | `/{id}/leader-unavailabilities/{unavailability_id}` | PATCH | R(PLANNER) | AUDIT | RL |
| | | DELETE | R(PLANNER) | AUDIT | RL |
| | `/{district_id}/feiertage/states` | GET | 🔐 Auth | – | RL |
| | `/{district_id}/feiertage` | POST | R(DISTRICT_ADMIN) | AUDIT | RL |
| **events_compat** | `/api/v1/events?district_id=...` | GET | R(VIEWER) | – | RL |
| | `/api/v1/events/{event_id}` | PATCH | R(PLANNER) | AUDIT | RL |
| | `/api/v1/events/{event_id}/resolve-deviation` | POST | R(PLANNER) | AUDIT | RL |
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
- `docs/architecture-status.md` — aktueller Architekturstatus
- `docs/improvement-proposals.md` — dokumentierte Verbesserungs- und Restarbeiten
- `services/backend/scripts/check_rbac_guard_pattern.py` — CI-Lint-Regel für RBAC-Guard-Pattern

## Generiertes Endpoint-Inventar

Nicht manuell bearbeiten — neu erzeugen mit
`cd services/backend && uv run python scripts/rbac_coverage_report.py`.
`test_permission_coverage.py` prüft, dass dieser Abschnitt aktuell ist.

<!-- rbac-inventory:start -->
| Methode | Pfad | Handler | Authentifizierung | Guards |
|---|---|---|---|---|
| GET, HEAD, OPTIONS | `/api/health` | `health.health` | 🔓 Public | – |
| GET | `/api/v1/auth/access` | `auth.get_access_context` | 🔐 Auth | `get_districts_where_user_has_role`, `is_superadmin` |
| GET | `/api/v1/auth/me` | `auth.get_current_user_info` | 🔐 Auth | `is_superadmin` |
| GET | `/api/v1/auth/oidc/discovery` | `auth.get_oidc_discovery` | 🔓 Public | – |
| POST | `/api/v1/auth/oidc/token` | `auth.exchange_oidc_token` | 🔓 Public | – |
| GET | `/api/v1/calendar-integrations` | `calendar_integrations.list_calendar_integrations` | 🔐 Auth | `assert_has_role_in_congregation`, `is_superadmin`, `require_role_in_district` |
| POST | `/api/v1/calendar-integrations` | `calendar_integrations.create_calendar_integration` | 🔐 Auth | `assert_has_role_in_congregation`, `require_role_in_district` |
| DELETE | `/api/v1/calendar-integrations/{integration_id}` | `calendar_integrations.delete_calendar_integration` | 🔐 Auth | `assert_has_role_in_congregation`, `require_role_in_district` |
| PATCH | `/api/v1/calendar-integrations/{integration_id}` | `calendar_integrations.update_calendar_integration` | 🔐 Auth | `assert_has_role_in_congregation`, `require_role_in_district` |
| POST | `/api/v1/calendar-integrations/{integration_id}/sync` | `calendar_integrations.trigger_sync` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts` | `districts.list_districts` | 🔐 Auth | `get_districts_where_user_has_role`, `is_superadmin` |
| POST | `/api/v1/districts` | `districts.create_district` | 🔐 Auth | `require_superadmin` |
| PATCH | `/api/v1/districts/{district_id}` | `districts.update_district` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/congregations` | `districts.list_congregations` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/congregations` | `districts.create_congregation` | 🔐 Auth | `require_role_in_district` |
| PATCH | `/api/v1/districts/{district_id}/congregations/{congregation_id}` | `districts.update_congregation` | 🔐 Auth | `assert_has_role_in_congregation`, `assert_has_role_in_district` |
| POST | `/api/v1/districts/{district_id}/feiertage` | `districts.import_feiertage_endpoint` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/feiertage/states` | `districts.list_de_states` | 🔐 Auth | – |
| POST | `/api/v1/districts/{district_id}/generate-planning-series` | `districts.generate_planning_series_slots` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/groups` | `districts.list_groups` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/groups` | `districts.create_group` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/districts/{district_id}/groups/{group_id}` | `districts.delete_group` | 🔐 Auth | `require_role_in_district` |
| PATCH | `/api/v1/districts/{district_id}/groups/{group_id}` | `districts.update_group` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/leader-unavailabilities` | `leader_unavailabilities.list_unavailabilities` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/leader-unavailabilities` | `leader_unavailabilities.create_unavailability` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/districts/{district_id}/leader-unavailabilities/{unavailability_id}` | `leader_unavailabilities.delete_unavailability` | 🔐 Auth | `require_role_in_district` |
| PATCH | `/api/v1/districts/{district_id}/leader-unavailabilities/{unavailability_id}` | `leader_unavailabilities.update_unavailability` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/leaders` | `leaders.list_leaders` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/leaders` | `leaders.create_leader` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/districts/{district_id}/leaders/link-self` | `leaders.unlink_self_from_leader` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/leaders/link-self` | `leaders.get_self_link` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/leaders/link-self` | `leaders.link_self_to_leader` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/districts/{district_id}/leaders/{leader_id}` | `leaders.delete_leader` | 🔐 Auth | `require_role_in_district` |
| PATCH | `/api/v1/districts/{district_id}/leaders/{leader_id}` | `leaders.update_leader` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/matrix` | `districts.get_matrix` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/matrix/generate-drafts` | `districts.generate_matrix_drafts` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/districts/{district_id}/registrations` | `registrations.list_registrations` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/registrations` | `registrations.submit_registration` | 🔓 Public | – |
| DELETE | `/api/v1/districts/{district_id}/registrations/{registration_id}` | `registrations.delete_registration` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/registrations/{registration_id}/approve` | `registrations.approve_registration` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/districts/{district_id}/registrations/{registration_id}/reject` | `registrations.reject_registration` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/events` | `events.list_events` | 🔐 Auth | `is_superadmin`, `require_role_in_district` |
| POST | `/api/v1/events/bulk-approval-status` | `events.bulk_update_approval_status` | 🔐 Auth | `is_superadmin`, `require_role_in_district` |
| PATCH | `/api/v1/events/{event_id}` | `events.update_event` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/events/{event_id}/assignments` | `service_assignments.list_assignments` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/events/{event_id}/assignments` | `service_assignments.create_assignment` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/events/{event_id}/assignments/{assignment_id}` | `service_assignments.delete_assignment` | 🔐 Auth | `require_role_in_district` |
| PUT | `/api/v1/events/{event_id}/assignments/{assignment_id}` | `service_assignments.update_assignment` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/events/{event_id}/invitations` | `invitations.list_event_invitations` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/events/{event_id}/invitations` | `invitations.create_invitations` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/events/{event_id}/resolve-deviation` | `events.resolve_event_deviation` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/export-tokens` | `export.list_export_tokens` | 🔐 Auth | `is_superadmin`, `require_role_in_district` |
| POST | `/api/v1/export-tokens` | `export.create_export_token` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/export-tokens/{token_id}` | `export.delete_export_token` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/export/{token_str}/calendar.ics` | `export.export_calendar_ics` | 🔓 Public | – |
| GET | `/api/v1/external-candidates` | `external_candidates.list_candidates` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/external-candidates/{candidate_id}/accept` | `external_candidates.accept_candidate` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/external-candidates/{candidate_id}/dismiss` | `external_candidates.dismiss_candidate` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/invitations/overwrite-requests` | `invitations.list_overwrite_requests` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/invitations/overwrite-requests/{request_id}/decision` | `invitations.decide_overwrite_request` | 🔐 Auth | `require_role_in_district` |
| DELETE | `/api/v1/invitations/{invitation_id}` | `invitations.remove_invitation` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/notifications/{district_id}` | `notifications.list_notifications` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/notifications/{district_id}/read-all` | `notifications.mark_all_read` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/notifications/{district_id}/unread-count` | `notifications.unread_count` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/notifications/{notification_id}/dismiss` | `notifications.dismiss_notification` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/notifications/{notification_id}/read` | `notifications.mark_read` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/planning-series` | `planning_series.create_planning_series` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/planning-series/districts/{district_id}/generate-slots` | `planning_series.generate_slots_for_district` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/planning-series/generate-all-slots` | `planning_series.generate_all_slots` | 🔐 Auth | `require_superadmin` |
| GET | `/api/v1/planning-series/{series_id}` | `planning_series.get_planning_series` | 🔐 Auth | `require_role_in_district` |
| PATCH | `/api/v1/planning-series/{series_id}` | `planning_series.update_planning_series` | 🔐 Auth | `require_role_in_district` |
| POST | `/api/v1/planning-series/{series_id}/generate-slots` | `planning_series.generate_slots_for_series` | 🔐 Auth | `require_role_in_district` |
| GET | `/api/v1/public/districts` | `registrations.list_districts_public` | 🔓 Public | – |
| GET | `/api/v1/public/districts/{district_id}/congregations` | `registrations.list_congregations_public` | 🔓 Public | – |
| GET | `/api/v1/registrations/pending-overview` | `registrations.get_pending_overview` | 🔐 Auth | `get_districts_where_user_has_role`, `is_superadmin` |
| POST | `/api/v1/system/update` | `system.trigger_update` | 🔐 Auth | `is_superadmin` |
| GET | `/api/v1/system/version` | `system.get_version` | 🔐 Auth | `get_districts_where_user_has_role`, `is_superadmin` |
| GET, HEAD, OPTIONS | `/health` | `health.health` | 🔓 Public | – |
<!-- rbac-inventory:end -->
