## Why

Nach der Freigabe legt das Backend Benutzer direkt über die Keycloak Admin API an und verschickt die Einladungsmail. Dafür meldet es sich heute mit einem Admin-Benutzer des **master**-Realms per Password-Grant (`admin-cli`) an. Ein kompromittiertes Backend hätte damit Vollzugriff auf alle Realms; zudem steht ein Admin-Passwort in der `.env` (OWASP ASVS V1/V4: Least Privilege). Die Einladungslinks laufen nur mit dem Realm-Standard ab und führen nach dem Passwortsetzen nicht zurück in die Anwendung.

## What Changes

- **BREAKING:** Der Keycloak-Provisioner authentifiziert sich nur noch per `client_credentials` mit einem eigenen Confidential Client (Service Account) im App-Realm. Der Service Account erhält ausschließlich `realm-management`-Rollen `manage-users` und `view-users`. `IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME`/`_PASSWORD` entfallen; neu sind `IDP_PROVISIONING_KEYCLOAK_CLIENT_ID`/`_CLIENT_SECRET`.
- Der Produktions-Guard verweigert den Start, wenn der Keycloak-Provider ohne Client-Credentials konfiguriert ist oder noch die alten Admin-Variablen gesetzt sind.
- Die Einladungsmail (`execute-actions-email`) erhält eine begrenzte Gültigkeit (`lifespan`, Standard 72 h, erlaubt 1 h bis 7 Tage) und, sofern konfiguriert, `client_id` und `redirect_uri`, damit die Person nach dem Passwortsetzen in der Anwendung landet.
- Das Realm-Setup-Skript (`idp-deploy/keycloak/setup_keycloak_realm.py`) legt den Provisioning-Client mit minimalen Rollen an und setzt sichere Realm-Defaults: Selbstregistrierung aus, E-Mail-Verifikation an, Brute-Force-Schutz an, Passwort-Policy (mind. 12 Zeichen, nicht gleich Benutzername/E-Mail).
- Dokumentation: Freigabe-Workflow, OIDC-Setup, `.env.example` und Produktions-Runbook beschreiben SMTP im Realm (gleiches Relay wie die App), den Service Account, die Migration und die Empfehlung OTP/Passkey für Bezirksadmins.

## Capabilities

### New Capabilities

### Modified Capabilities
- `approved-user-onboarding`: Neue Anforderungen an die Zugangsdaten der Keycloak-Provisionierung (Least Privilege, kein master-Realm-Admin) und an Einladungslinks (begrenzte Gültigkeit, Rücksprung in die App).

## Impact

- Backend: `app/adapters/idp/keycloak_provisioner.py`, `app/adapters/idp/provisioning.py`, `app/config.py` (Settings und Produktions-Guard), Unit-Tests `tests/unit/test_provisioning_unit.py` und Config-Tests.
- IdP-Deployment: `idp-deploy/keycloak/setup_keycloak_realm.py` und dessen Test, `idp-deploy/keycloak/OIDC-SETUP.md`.
- Konfiguration/Doku: `.env.example`, `docs/features/approval-workflow.md`, `docs/operations/production-runbook.md`.
- Betrieb: Bestehende Installationen mit `IDP_PROVISIONING_PROVIDER=keycloak` müssen vor dem Update den Service-Account-Client anlegen und die neuen Variablen setzen. Webhook-Provider und deaktivierte Provisionierung sind nicht betroffen.
- Kein neuer Mailserver: Keycloak nutzt das bereits für die App vorgeschriebene SMTP-Relay.
