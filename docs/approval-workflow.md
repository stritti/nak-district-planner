# Freigabe-Workflow fuer IDP-Benutzer

Dieses Dokument beschreibt den produktiven Onboarding-Ablauf fuer Benutzer, die sich ueber OIDC/IDP anmelden.

## Ziel

- Anmeldung bleibt IDP-basiert (OIDC).
- Fachzugriff wird erst nach interner Freigabe aktiviert.
- Zugriff wird strikt auf den zugewiesenen Scope (Bezirk oder Gemeinde) begrenzt.

## Ablauf

1. Benutzer registriert sich ueber die oeffentliche Registrierungsseite.
2. Optional mitgesendeter Bearer-Token wird validiert; bei ungueltigem Token wird `401` geliefert.
3. Registrierung landet als `PENDING` im Bezirk.
4. Bezirksadministrator genehmigt mit:
   - `role` (`DISTRICT_ADMIN`, `CONGREGATION_ADMIN`, `PLANNER`, `VIEWER`)
   - `scope_type` (`DISTRICT` oder `CONGREGATION`)
   - `scope_id` (UUID des Bezirkes oder der Gemeinde)
5. Bei genehmigter Registrierung wird eine Membership erzeugt oder aktualisiert.
6. Optional (empfohlen): Benutzer wird beim Approval automatisch im IDP angelegt.
7. Nach Login ist der Benutzer aktiv, sobald mindestens eine Membership vorhanden ist.

## Wichtige Regeln

- Pro Approval wird initial genau eine Membership gesetzt.
- Standardrolle im Freigabe-Dialog ist `PLANNER`.
- Benutzer ohne Membership erhalten auf geschuetzten Endpunkten `403` mit Hinweis auf ausstehende Freigabe.
- `superadmin` ist von der Membership-Pflicht ausgenommen.

## API-Hinweise

- `GET /api/v1/auth/me`: liefert Identitaet (auch vor Freigabe nutzbar)
- `GET /api/v1/auth/access`: liefert effektive Memberships und Status
  - `ACTIVE`: Zugriff freigegeben
  - `PENDING_APPROVAL`: angemeldet, aber keine Membership vorhanden

## IDP-Provisionierung bei Genehmigung

Der Planner unterstuetzt zwei Modi:

- `webhook`: ruft einen externen Provisioning-Service auf
- `keycloak`: spricht direkt die Keycloak Admin API an

Empfohlener Produktionsmodus, wenn Keycloak direkt genutzt wird:

```env
IDP_PROVISIONING_ENABLED=true
IDP_PROVISIONING_PROVIDER=keycloak
IDP_PROVISIONING_KEYCLOAK_BASE_URL=https://auth.example.com
IDP_PROVISIONING_KEYCLOAK_REALM=nak-planner
IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME=admin
IDP_PROVISIONING_KEYCLOAK_ADMIN_PASSWORD=<secret>
IDP_PROVISIONING_KEYCLOAK_INVITE_ON_APPROVAL=true
```

Verhalten im Keycloak-Modus bei Approval:

1. User wird per E-Mail gesucht.
2. Falls nicht vorhanden: User wird angelegt (`username=email`, `email`, `enabled=true`).
3. Falls `IDP_PROVISIONING_KEYCLOAK_INVITE_ON_APPROVAL=true`: Keycloak sendet E-Mail mit Required Actions (`VERIFY_EMAIL`, `UPDATE_PASSWORD`).
4. Ergebnis wird in Registrierung gespeichert (`idp_provision_status`, ggf. `idp_provision_error`).

## Betrieb / Rollout

- Vor Aktivierung des Membership-Gates bestehende Benutzer pruefen und ggfs. backfillen.
- Siehe Runbook: `docs/membership-backfill-runbook.md`.
