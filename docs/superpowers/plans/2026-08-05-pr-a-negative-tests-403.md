# PR A — Negative-Tests: 403 bei falscher Rolle (p0 2.5)

## Ziel

`test_protected_endpoints.py` deckt bisher nur **401** ab (fehlendes/ungültiges Token).
p0 2.5 verlangt zusätzlich **403 bei falscher Rolle**: ein authentifizierter Benutzer
mit gültigem Token, aber ohne die für die Route erforderliche Rolle, muss `403` erhalten.

Dieser Plan ergänzt Integrationstests für alle geschützten Routen. Falls ein Test einen
fehlenden/fehlerhaften Guard aufdeckt, wird der Guard korrigiert und `docs/roles.md`
konsistent gehalten.

## Ausgangslage (verifiziert)

- Permission-Layer: `app/adapters/auth/permissions.py`
  - `require_role_in_district(auth, Role.X, district_id)` → wirft `PermissionError` → 403
  - `assert_has_role_in_district` / `assert_has_role_in_congregation` → 403
  - `has_role_in_district` / `has_role_in_congregation` → bool
- `Role`-StrEnum in `app/domain/models/role.py`: `DISTRICT_ADMIN`, `CONGREGATION_ADMIN`, `PLANNER`, `VIEWER`
- Auth-Injection für Tests: `app/adapters/api/deps.py`
  - `set_token_claims(claims)` / `get_token_claims()`
  - `get_current_user_with_memberships` liest Memberships aus `claims["memberships"]`
    via `jwt_claims.py::extract_memberships_from_claims` (je `{role, scope_type, scope_id}`)
  - `require_membership_access` → 403 „Freigabe ausstehend" nur wenn memberships leer
- Etabliertes Muster in `tests/unit/test_router_districts.py`:
  - `patch("app.adapters.api.routers.districts.assert_has_role_in_district")` mit
    `side_effect=HTTPException(status_code=403)`, oder
  - `set_token_claims` mit `"memberships": [Membership.create(...)]`
- **pre-guard Rest-Ressourcen-Loads** (müssen gemockt sein, sonst 404 statt 403):
  - events_compat PATCH `/events/{id}` → `SqlPlanningSlotRepository.get`
  - calendar_integrations POST/PATCH/DELETE `/{id}` + `/{id}/sync` → `SqlCalendarIntegrationRepository.get`
  - export DELETE `/export-tokens/{id}` → Token-Repo `.get`
  - invitations POST/GET `/events/{id}/invitations`, DELETE `/invitations/{id}`,
    POST `/invitations/overwrite-requests/{id}/decision` → Slot-Repo `.get`
  - leaders POST `/leaders/{id}/link-self` → Leader-Repo `.get`
  - notifications POST `/{notification_id}/read` → `NotificationService.get`
  - planning_series GET/PATCH `/{id}`, POST `/{id}/generate-slots` → `SqlPlanningSeriesRepository.get`
  - service_assignments → Slot-Repo `.get`

## Strategie

Ein gemeinsamer Helper baut einen `TestClient`, dessen Benutzer per JWT-Claim-Injection
eine **niedrige Rolle** (VIEWER) in einem District hält. Für Routen, die DISTRICT_ADMIN
verlangen, ist VIEWER zu niedrig → 403. Für Routen, die nur VIEWER verlangen, wird ein
Benutzer **ohne** Membership im Ziel-District verwendet (leere memberships → 403 via
`require_membership_access` bzw. fehlende Rolle).

Helper wird in `tests/integration/test_protected_routes_403.py` als Modul-Funktion
definiert (selbst-enthaltend, analog `_superadmin_auth()`).

## Tasks

### Task 1 — Shared Helper `_auth_client`

In `tests/integration/test_protected_routes_403.py`:

```python
def _auth_client(mock_oidc_adapter, role: Role | None, district_id: uuid.UUID | None) -> TestClient:
    """Build a TestClient whose user holds `role` in `district_id` (via JWT claims).

    role=None + district_id=None → user with NO memberships (403 via require_membership_access).
    """
    memberships = []
    if role is not None and district_id is not None:
        memberships = [
            {"role": role.value, "scope_type": "DISTRICT", "scope_id": str(district_id)}
        ]
    claims = {
        "sub": "user-403",
        "email": "user403@example.com",
        "preferred_username": "user403",
        "name": "User 403",
        "memberships": memberships,
    }
    mock_oidc_adapter.validate_token.return_value = claims
    mock_oidc_adapter.extract_user_info.return_value = {
        "sub": "user-403",
        "email": "user403@example.com",
        "username": "user403",
        "name": "User 403",
        "given_name": None,
        "family_name": None,
    }
    with (
        patch("app.adapters.api.deps.SqlUserRepository") as MockUserRepo,
        patch("app.adapters.api.deps.SqlLeaderRegistrationRepository") as MockRegRepo,
    ):
        user_repo = AsyncMock()
        user_repo.get_by_sub.return_value = None
        user_repo.has_any_user.return_value = True  # is_superadmin = False
        user_repo.save = AsyncMock()
        MockUserRepo.return_value = user_repo

        reg_repo = AsyncMock()
        reg_repo.list_approved_unlinked_by_email.return_value = []
        MockRegRepo.return_value = reg_repo

        return TestClient(app)
```

**Verifikation:** `pytest tests/integration/test_protected_routes_403.py -k helper -v` (Smoke).

### Task 2 — districts Router (403)

Routen (alle guarden direkt auf `district_id`-Pfad/Query, kein pre-guard Load):
- `PATCH /api/v1/districts/{id}` (DISTRICT_ADMIN)
- `POST /api/v1/districts/{id}/congregations` (DISTRICT_ADMIN)
- `GET /api/v1/districts/{id}/congregations` (VIEWER)
- `POST /api/v1/districts/{id}/groups` (DISTRICT_ADMIN)
- `GET /api/v1/districts/{id}/groups` (VIEWER)
- `POST /api/v1/districts` (superadmin — VIEWER → 403)

Test je Route: `_auth_client(mock_oidc_adapter, Role.VIEWER, district_id)` → erwartet 403.
Für superadmin-Route `create_district`: VIEWER-Benutzer (kein superadmin) → 403.

### Task 3 — calendar_integrations + export Router (403)

calendar_integrations (DISTRICT_ADMIN):
- `POST /api/v1/calendar-integrations` (guard auf body.district_id)
- `GET /api/v1/calendar-integrations?district_id=...`
- `POST /api/v1/calendar-integrations/{id}/sync` → **mock** `SqlCalendarIntegrationRepository.get` → Integration mit `district_id`
- `PATCH /api/v1/calendar-integrations/{id}` → mock Repo
- `DELETE /api/v1/calendar-integrations/{id}` → mock Repo

export (DISTRICT_ADMIN):
- `POST /api/v1/export-tokens` (guard auf body.district_id)
- `GET /api/v1/export-tokens?district_id=...`
- `DELETE /api/v1/export-tokens/{id}` → mock Token-Repo `.get`

### Task 4 — events_compat + service_assignments + invitations Router (403)

events_compat:
- `GET /api/v1/events?district_id=...` (VIEWER)
- `PATCH /api/v1/events/{id}` (DISTRICT_ADMIN) → mock `SqlPlanningSlotRepository.get` → Slot mit `district_id`
- `POST /api/v1/events/bulk-approval-status?district_id=...` (DISTRICT_ADMIN)

service_assignments (DISTRICT_ADMIN):
- `POST /api/v1/events/{id}/assignments` → mock Slot-Repo `.get`
- `PATCH /api/v1/events/{id}/assignments/{assignment_id}` → mock Slot-Repo `.get`
- `DELETE /api/v1/events/{id}/assignments/{assignment_id}` → mock Slot-Repo `.get`

invitations:
- `POST /api/v1/events/{id}/invitations` (DISTRICT_ADMIN) → mock Slot-Repo `.get`
- `GET /api/v1/events/{id}/invitations` (VIEWER) → mock Slot-Repo `.get`
- `DELETE /api/v1/invitations/{id}` (DISTRICT_ADMIN) → mock Slot-Repo `.get`
- `GET /api/v1/invitations/overwrite-requests?district_id=...` (DISTRICT_ADMIN)
- `POST /api/v1/invitations/overwrite-requests/{id}/decision` (DISTRICT_ADMIN) → mock Req+Slot

### Task 5 — leaders + notifications + planning_series Router (403)

leaders:
- `GET /api/v1/districts/{id}/leaders` (VIEWER)
- `POST /api/v1/districts/{id}/leaders` (DISTRICT_ADMIN)
- `POST /api/v1/districts/{id}/leaders/{leader_id}/link-self` (VIEWER) → mock Leader-Repo `.get`
- `DELETE /api/v1/districts/{id}/leaders/{leader_id}` (DISTRICT_ADMIN)

notifications:
- `GET /api/v1/notifications?district_id=...` (VIEWER)
- `POST /api/v1/notifications/{notification_id}/read` (VIEWER) → mock `NotificationService.get` → Notification mit `district_id`
- `POST /api/v1/notifications/{district_id}/read-all` (VIEWER)

planning_series (DISTRICT_ADMIN, außer GET=VIEWER):
- `POST /api/v1/planning-series` (guard auf body.district_id)
- `GET /api/v1/planning-series/{id}` (VIEWER) → mock `SqlPlanningSeriesRepository.get`
- `PATCH /api/v1/planning-series/{id}` (DISTRICT_ADMIN) → mock Repo
- `POST /api/v1/planning-series/{id}/generate-slots` (DISTRICT_ADMIN) → mock Repo
- `POST /api/v1/planning-series/generate-district-slots` (DISTRICT_ADMIN, guard auf body.district_id)
- `POST /api/v1/planning-series/generate-all-slots` (superadmin → VIEWER → 403)

### Task 6 — registrations + system Router (403)

registrations:
- `GET /api/v1/districts/{id}/registrations` (VIEWER)
- `POST /api/v1/districts/{id}/registrations` (DISTRICT_ADMIN)
- `GET /api/v1/registrations/overview?district_id=...` (VIEWER)
- `POST /api/v1/registrations/{id}/approve` (DISTRICT_ADMIN)
- `POST /api/v1/registrations/{id}/reject` (DISTRICT_ADMIN)

system:
- `GET /api/v1/system/version` (VIEWER mit Membership im District → 200; Benutzer ohne Membership → 403)
- `POST /api/v1/system/update` (superadmin → VIEWER → 403)

### Task 7 — Verifikation + Doku + Commit

1. `pytest tests/integration/test_protected_routes_403.py -v` → alle 403-Tests grün.
2. `pytest tests/integration/ -v` → keine Regression (insb. `test_protected_endpoints.py`).
3. Falls ein Test einen fehlenden Guard aufdeckt: Guard ergänzen, `docs/roles.md` prüfen.
4. p0 Task 2.5 in `docs/superpowers/tasks.md` abhaken.
5. Commit auf Branch `feat/pr-a-negative-tests-403` (Stil: `refactor: ... (PR-Nr)`), PR erstellen.

## Verifikations-Baseline

- Backend: `pytest` (pyproject: `asyncio_mode="auto"`, testpaths tests).
- Integrationstests laufen gegen Mock-OIDC + `app.dependency_overrides[deps.get_db_session]`
  (Muster in `test_matrix_endpoint.py`).
- Kein Designer nötig (kein visuelles UI). Headless/mechanisch → @fixer-Lane.