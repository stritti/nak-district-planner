## Why

Seit `harden-keycloak-provisioning` meldet sich das Backend mit einem Service Account im App-Realm an, der die Rollen `manage-users` und `view-users` von `realm-management` hat. `manage-users` erlaubt aber mehr als nötig: Rollen zuordnen, Gruppenmitgliedschaften ändern und Benutzer löschen. Ein kompromittiertes Backend könnte damit Konten im Realm übernehmen oder Keycloak-Rollen vergeben (OWASP ASVS V4, Least Privilege). Keycloak ab 26.2 bietet feingranulare Admin-Berechtigungen (FGAP v2), mit denen sich das auf die tatsächlich benötigten Operationen begrenzen lässt. Die Entscheidung, das als eigenen Change nachzuziehen, fiel im Review von PR #679.

## What Changes

- Das Realm-Setup-Skript aktiviert *Admin Permissions* (FGAP v2) im App-Realm und legt für den Service Account `nak-planner-provisioning` eine Client-Policy sowie Users-Permissions nur mit den benötigten Scopes an (Suchen/Lesen, Anlegen bzw. Verwalten, Pflichtaktionen per E-Mail auslösen). Die Scopes `map-roles`, `manage-group-membership`, `impersonate` und `delegate` werden nicht vergeben.
- Die `realm-management`-Rollen `manage-users` und `view-users` werden dem Service Account entzogen, weil eine Legacy-Rolle die Auswertung der feingranularen Berechtigungen umgeht.
- Ein Integrationstest gegen einen echten Keycloak (Version wie in `docker-compose.prod.yml`) belegt: Anlegen, Suchen und Einladen funktionieren; Rollenzuordnung, Gruppenänderung und Löschen werden mit 403 abgelehnt.
- Dokumentation (Freigabe-Workflow, `production-compose.md`, OIDC-Setup) und eine Upgrade-Notiz beschreiben die Umstellung und die Mindestversion Keycloak 26.2.
- Der Backend-Code bleibt unverändert; nur die Rechte des Service Accounts ändern sich.

## Capabilities

### New Capabilities

### Modified Capabilities
- `approved-user-onboarding`: Neue Anforderung, dass der Provisioning-Zugang keine Rollen- oder Gruppenzuordnungen und kein Löschen von Benutzern erlaubt.

## Impact

- IdP-Deployment: `idp-deploy/keycloak/setup_keycloak_realm.py` und `services/backend/tests/unit/test_keycloak_setup_script.py`; neuer Integrationstest gegen Keycloak (Testcontainer oder Compose-Service im CI).
- Dokumentation: `docs/features/approval-workflow.md`, `docs/operations/production-compose.md`, `idp-deploy/keycloak/OIDC-SETUP.md`, neue Datei in `docs/operations/release-notes/`.
- Betrieb: Bestehende Installationen führen das Setup-Skript erneut aus oder richten die Permissions in der Admin-Konsole ein. Installationen mit externem Keycloak unter 26.2 behalten den bisherigen Rollen-Ansatz (dokumentierter Fallback).
- Keine Änderung an Backend-API, Datenbank oder Frontend.
