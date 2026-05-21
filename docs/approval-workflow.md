# Freigabe-Workflow fuer IDP-Benutzer

Dieses Dokument beschreibt den produktiven Onboarding-Ablauf fuer Benutzer, die sich ueber OIDC/IDP anmelden.

## Ziel

- Anmeldung bleibt IDP-basiert (OIDC).
- Fachzugriff wird erst nach interner Freigabe aktiviert.
- Zugriff wird strikt auf den zugewiesenen Scope (Bezirk oder Gemeinde) begrenzt.

## Ablauf (Überblick)

1. Benutzer registriert sich ueber die oeffentliche Registrierungsseite (`POST /api/v1/districts/{id}/registrations`).
2. Optional mitgesendeter Bearer-Token wird validiert; bei ungueltigem Token wird `401` geliefert.
3. Registrierung landet als `PENDING` im Bezirk.
4. Bezirksadministrator genehmigt (`POST .../{registration_id}/approve`):
   - `role` (`DISTRICT_ADMIN`, `CONGREGATION_ADMIN`, `PLANNER`, `VIEWER`)
   - `scope_type` (`DISTRICT` oder `CONGREGATION`)
   - `scope_id` (UUID des Bezirkes oder der Gemeinde)
5. Bei Genehmigung wird ein `Leader`-Datensatz, eine `Membership` **und** (optional) ein IdP-Benutzer erstellt.
6. Registrierter Benutzer erhaelt eine Einladungsmail (wenn konfiguriert) und muss beim ersten Login sein Passwort setzen.
7. Nach Login ist der Benutzer aktiv, sobald mindestens eine Membership vorhanden ist.

## Detaillierter Ablauf bei Genehmigung

Nachfolgend wird Schritt für Schritt beschrieben, was im Backend passiert, wenn ein Bezirksadministrator eine Registrierung freigibt.

```
Approval-Request
    │
    ├─ 1. Leader-Datensatz anlegen
    ├─ 2. Registration auf APPROVED setzen
    ├─ 3. Membership anlegen (wenn user_sub bekannt)
    ├─ 4. IdP-Provisioning (optional)
    │      ├─ 4a. User im IdP suchen (per E-Mail)
    │      ├─ 4b. Ggf. neu anlegen
    │      └─ 4c. Einladungsmail senden (VERIFY_EMAIL + UPDATE_PASSWORD)
    └─ 5. Ergebnis in Registration speichern (idp_provision_status)
```

### Schritt 1–3: Leader, Status, Membership

**Datei:** `services/backend/app/adapters/api/routers/registrations.py` (ab Zeile 270)

```python
# Leader anlegen
leader = Leader.create(name=..., district_id=..., rank=..., congregation_id=...)
await SqlLeaderRepository(db).save(leader)

# Registration als APPROVED markieren
reg.status = RegistrationStatus.APPROVED
reg.assigned_role = body.role
reg.assigned_scope_type = body.scope_type
reg.assigned_scope_id = body.scope_id
reg.approved_by_sub = auth.user_sub
reg.approved_at = datetime.now(UTC)

# Membership anlegen (wenn Benutzer bereits via OIDC verbunden)
if reg.user_sub is not None:
    await SqlMembershipRepository(db).upsert_by_scope(
        user_sub=reg.user_sub,
        role=body.role,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
    )
```

### Schritt 4: IdP-Provisioning

**Datei:** `services/backend/app/adapters/idp/provisioning.py`

Der Provisioner wird über `get_idp_provisioner()` ermittelt. Verfügbare Provider:

| Provider | Konfiguration | Beschreibung |
|----------|--------------|-------------|
| `keycloak` | `IDP_PROVISIONING_PROVIDER=keycloak` + Keycloak-Admin-URL/Realm/Credentials | Direkte Kommunikation mit der Keycloak Admin API |
| `webhook` | `IDP_PROVISIONING_PROVIDER=webhook` + `IDP_PROVISIONING_ENDPOINT` | POST an externen Provisioning-Service |
| deaktiviert | `IDP_PROVISIONING_ENABLED=false` (Default) | Keine IdP-Provisionierung |

Falls kein Provider konfiguriert ist (`get_idp_provisioner()` gibt `None` zurück), wird die Freigabe trotzdem durchgeführt — nur ohne IdP-Anlage.

### Schritt 4a–4c: Keycloak-Provisionierung im Detail

**Datei:** `services/backend/app/adapters/idp/keycloak_provisioner.py`

```
provision_user(email, name, ...)
    │
    ├─ _get_admin_token()
    │   POST /realms/master/protocol/openid-connect/token
    │   → Admin-Access-Token (Client: admin-cli, Password-Grant)
    │
    ├─ _find_user_by_email(token, email)
    │   GET /admin/realms/{realm}/users?email=...&exact=true
    │   → Vorhandenen User suchen, ggf. überspringen
    │
    ├─ _create_user(token, email, name)  [nur wenn nicht vorhanden]
    │   POST /admin/realms/{realm}/users
    │   {
    │     "username": email,
    │     "email": email,
    │     "enabled": true,
    │     "emailVerified": false,
    │     "firstName": "Vorname",
    │     "lastName": "Nachname"
    │   }
    │   → User-ID (aus Location-Header oder Lookup)
    │
    └─ _trigger_invite(token, user_id)  [nur wenn invite_on_approval=true]
        PUT /admin/realms/{realm}/users/{id}/execute-actions-email
        ["VERIFY_EMAIL", "UPDATE_PASSWORD"]
        → Keycloak sendet E-Mail mit Link zum Passwort-Setzen
```

**Wichtig:** Die `_trigger_invite`-Methode sendet die Keycloak-eigene Einladungsmail. Der Benutzer muss darin:
1. Seine **E-Mail-Adresse bestätigen** (`VERIFY_EMAIL`)
2. Ein **Passwort setzen** (`UPDATE_PASSWORD`)

Erst nach diesen beiden Schritten ist der Account aktiv und der Login möglich.

### Schritt 4 (Alternativ): Webhook-Provisionierung

**Datei:** `services/backend/app/adapters/idp/webhook_provisioner.py`

Sendet einen HTTP-POST an eine konfigurierte externe URL:

```json
POST {endpoint}
Authorization: Bearer {api_key}
{
  "email": "...",
  "name": "...",
  "district_id": "...",
  "registration_id": "...",
  "role": "PLANNER",
  "scope_type": "DISTRICT",
  "scope_id": "..."
}
```

Erwartete Antwort:
```json
{
  "status": "CREATED_INVITED",
  "user_sub": "idp-user-uuid"
}
```

### Schritt 5: Ergebnis speichern

Nach dem Provisioning werden in der Registration gespeichert:
- `idp_provision_status`: z. B. `CREATED_INVITED`, `CREATED`, `EXISTING_INVITED`, `EXISTING`, `FAILED`
- `idp_provision_error`: Fehlermeldung bei Fehlschlag
- `idp_provisioned_at`: Zeitstempel

Falls der Registration bisher keine `user_sub` zugeordnet war, der Provisioner aber eine zurückgibt (z. B. Keycloak-ID), wird diese nachgetragen und die Membership entsprechend aktualisiert:

```python
if reg.user_sub is None and provision_result.user_sub:
    reg.user_sub = provision_result.user_sub
    await SqlMembershipRepository(db).upsert_by_scope(...)
```

## Passwort beim ersten Login — Infrastruktur im Detail

Der gesamte Ablauf von der Registrierung bis zum ersten Login setzt sich aus drei unabhängigen, aber zusammenwirkenden Mechanismen zusammen:

### 1. IdP-Provisioning (bei Freigabe, s. o.)

Der Benutzer wird im IdP angelegt und erhält eine E-Mail mit Link zum Passwort-Setzen (`UPDATE_PASSWORD` als Required Action). Solange der Benutzer kein Passwort gesetzt hat, kann er sich nicht einloggen.

### 2. Auto-Create User beim ersten Login (Backend)

**Datei:** `services/backend/app/adapters/api/deps.py` (Zeile 55–124)

Sobald der Benutzer sich zum ersten Mal mit einem gültigen OIDC-Token beim Backend einloggt, wird automatisch ein lokaler `User`-Datensatz angelegt:

```python
# Auto-create user on first login
new_user = User(
    sub=user_info["sub"],
    email=user_info["email"],
    username=user_info["username"],
    name=user_info["name"],
    given_name=user_info["given_name"],
    family_name=user_info["family_name"],
    is_superadmin=is_superadmin,
)
await user_repo.save(new_user)
```

Dieser Mechanismus ist unabhängig vom IdP-Provisioning. Wenn der Benutzer bereits existiert, werden nur die Daten aktualisiert.

### 3. Post-Login-Verknüpfung von Registrierungen

**Datei:** `services/backend/app/adapters/api/deps.py` (Zeile 170–201)

Nach dem Login sucht das System nach **genau einer** approvten, aber noch nicht verknüpften Registrierung mit derselben E-Mail-Adresse:

```python
candidates = await reg_repo.list_approved_unlinked_by_email(user.email)
if len(candidates) == 1:
    registration = candidates[0]
    registration.user_sub = user.sub  # Verknüpfung
    # Membership materialisieren
    await membership_repo.upsert_by_scope(
        user_sub=user.sub,
        role=registration.assigned_role,
        scope_type=registration.assigned_scope_type,
        scope_id=registration.assigned_scope_id,
    )
```

Dies ist für den Fall gedacht, dass die Registration ohne vorherigen Login (und damit ohne `user_sub`) eingereicht wurde. Sobald der Benutzer das erste Mal eingeloggt ist, wird die Verknüpfung automatisch hergestellt.

### Vollständiger Login-Ablauf (Sequenz)

```
Benutzer                         Browser/Frontend                   Backend                        Keycloak/IDP
   │                                    │                              │                              │
   │  1. E-Mail-Link (Passwort setzen)  │                              │                              │
   │◄────────────────────────────────────│                              │                              │
   │                                    │                              │                              │
   │  2. Passwort vergeben              │                              │                              │
   │────────────────────────────────────►                              │                              │
   │                                    │                              │                              │
   │  3. Login                          │                              │                              │
   │────────────────────────────────────►                              │                              │
   │                                    │  4. OIDC Authorization       │                              │
   │                                    │─────────────────────────────────────────────────────────────►│
   │                                    │◄─────────────────────────────────────────────────────────────│
   │                                    │  5. Token austauschen                                       │
   │                                    │─────────────────────────────────────────────────────────────►│
   │                                    │◄── JWT (access_token + refresh_token) ──────────────────────│
   │                                    │                              │                              │
   │                                    │  6. API-Call mit Bearer-Token│                              │
   │                                    │──────────────────────────────►                              │
   │                                    │                              │  7. Token validieren (JWKS)  │
   │                                    │                              │──────────────────────────────►│
   │                                    │                              │◄─────────────────────────────│
   │                                    │                              │  8. User auto-createn (wenn  │
   │                                    │                              │     nicht vorhanden)         │
   │                                    │                              │  9. Registration verknüpfen  │
   │                                    │                              │     (wenn 1 unlinked match)  │
   │                                    │◄── 200 OK + Membership ──────│                              │
   │◄────────────────────────────────────│                              │                              │
```

## Konfiguration

### Umgebungsvariablen

| Variable | Default | Beschreibung |
|----------|---------|-------------|
| `IDP_PROVISIONING_ENABLED` | `false` | Provisionierung aktivieren |
| `IDP_PROVISIONING_PROVIDER` | `webhook` | `keycloak` oder `webhook` |
| `IDP_PROVISIONING_ENDPOINT` | `None` | URL für Webhook-Provisioner |
| `IDP_PROVISIONING_API_KEY` | `None` | API-Key für Webhook-Provisioner |
| `IDP_PROVISIONING_TIMEOUT_SECONDS` | `10.0` | Timeout für HTTP-Requests |
| `IDP_PROVISIONING_KEYCLOAK_BASE_URL` | `None` | Keycloak-Basis-URL (z. B. `https://auth.example.com`) |
| `IDP_PROVISIONING_KEYCLOAK_REALM` | `None` | Keycloak-Realm-Name |
| `IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME` | `None` | Admin-User für Keycloak Admin API |
| `IDP_PROVISIONING_KEYCLOAK_ADMIN_PASSWORD` | `None` | Passwort des Admin-Users |
| `IDP_PROVISIONING_KEYCLOAK_INVITE_ON_APPROVAL` | `true` | Einladungsmail bei Freigabe senden |

### Produktions-Konfiguration (Keycloak)

```env
IDP_PROVISIONING_ENABLED=true
IDP_PROVISIONING_PROVIDER=keycloak
IDP_PROVISIONING_KEYCLOAK_BASE_URL=https://auth.example.com
IDP_PROVISIONING_KEYCLOAK_REALM=nak-planner
IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME=admin
IDP_PROVISIONING_KEYCLOAK_ADMIN_PASSWORD=<secret>
IDP_PROVISIONING_KEYCLOAK_INVITE_ON_APPROVAL=true
```

## Datenbank-Felder der Registration

Die Registration-Tabelle enthält folgende IdP-bezogene Felder:

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `idp_provision_status` | `str?` | Status der IdP-Provisionierung (`CREATED_INVITED`, `CREATED`, `EXISTING_INVITED`, `EXISTING`, `FAILED`) |
| `idp_provision_error` | `str?` | Fehlermeldung bei fehlgeschlagener Provisionierung |
| `idp_provisioned_at` | `datetime?` | Zeitpunkt der Provisionierung |

Diese Felder werden bei jeder Freigabe zunächst zurückgesetzt (`None`) und dann vom Provisioner befüllt.

## Im Frontend

**Datei:** `services/frontend/src/views/LeadersAdminView.vue` (ab Zeile 209)

Der IdP-Status wird im Admin-Dialog als Badge angezeigt:

```
APPROVED + IDP: CREATED_INVITED  →  blauer Badge "IDP: CREATED_INVITED"
APPROVED + IDP: FAILED           →  roter Badge "IDP: FAILED"
                                  + Fehlermeldung darunter (idp_provision_error)
```

## Wichtige Regeln

- Pro Approval wird initial genau eine Membership gesetzt.
- Standardrolle im Freigabe-Dialog ist `PLANNER`.
- Benutzer ohne Membership erhalten auf geschuetzten Endpunkten `403` mit Hinweis auf ausstehende Freigabe.
- `superadmin` ist von der Membership-Pflicht ausgenommen.
- Wenn IdP-Provisioning fehlschlägt, wird die Freigabe **trotzdem durchgeführt** — der Fehler wird in `idp_provision_error` vermerkt.
- Die Post-Login-Verknüpfung funktioniert nur, wenn genau **eine** unverknüpfte Registration zur E-Mail existiert. Bei mehreren wird keine automatische Verknüpfung vorgenommen (Log-Warning).

## API-Hinweise

- `GET /api/v1/auth/me`: liefert Identitaet (auch vor Freigabe nutzbar)
- `GET /api/v1/auth/access`: liefert effektive Memberships und Status
  - `ACTIVE`: Zugriff freigegeben
  - `PENDING_APPROVAL`: angemeldet, aber keine Membership vorhanden

## Betrieb / Rollout

- Vor Aktivierung des Membership-Gates bestehende Benutzer pruefen und ggfs. backfillen.
- Siehe Runbook: `docs/membership-backfill-runbook.md`.

## Code-Referenzen

| Komponente | Datei |
|-----------|-------|
| Approval-Endpoint | `services/backend/app/adapters/api/routers/registrations.py` (ab Zeile 270) |
| Provisioner-Factory | `services/backend/app/adapters/idp/provisioning.py` |
| Keycloak-Provisioner | `services/backend/app/adapters/idp/keycloak_provisioner.py` |
| Webhook-Provisioner | `services/backend/app/adapters/idp/webhook_provisioner.py` |
| Basis-Protokoll | `services/backend/app/adapters/idp/base.py` |
| Auto-Create + Login-Verknüpfung | `services/backend/app/adapters/api/deps.py` (Zeile 55–201) |
| IDP-Status im Frontend | `services/frontend/src/views/LeadersAdminView.vue` (ab Zeile 209) |
| Konfiguration | `services/backend/app/config.py` (Zeile 31–40) |
