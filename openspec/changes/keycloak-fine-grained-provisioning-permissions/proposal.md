## Why

Seit `harden-keycloak-provisioning` meldet sich das Backend mit einem Service Account im App-Realm an, der die Rollen `manage-users` und `view-users` von `realm-management` hat. `manage-users` erlaubt aber mehr als nötig: Rollen zuordnen, Gruppenmitgliedschaften ändern und Benutzer löschen. Ein kompromittiertes Backend könnte damit Konten im Realm übernehmen oder Keycloak-Rollen vergeben (OWASP ASVS V4, Least Privilege). Keycloak ab 26.2 bietet feingranulare Admin-Berechtigungen (FGAP v2), mit denen sich zumindest Rollen- und Gruppenzuordnungen, Impersonation und Delegation ausschließen lassen. Löschen bleibt möglich, weil Keycloak 26.8 Anlegen und `execute-actions-email` an denselben Scope `manage` bindet, der auch Löschen erlaubt. Die Entscheidung, das als eigenen Change nachzuziehen, fiel im Review von PR #679.

## What Changes

- Das Realm-Setup-Skript aktiviert *Admin Permissions* (FGAP v2) im App-Realm und legt eine Realm-Rolle `nak-planner-provisioner` für den Service Account `nak-planner-provisioning`, eine Role-Policy darauf sowie eine Users-Permission mit nur `view` und `manage` an. Die Scopes `map-roles`, `manage-group-membership`, `impersonate`, `reset-password` und `delegate` werden nicht vergeben. Das verbleibende Recht zum Löschen wird als Restrisiko dokumentiert.
- Die `realm-management`-Rollen `manage-users` und `view-users` werden dem Service Account entzogen, weil eine Legacy-Rolle die Auswertung der feingranularen Berechtigungen umgeht.
- Ein Integrationstest gegen einen echten Keycloak (Version wie in `docker-compose.prod.yml`) belegt: Anlegen, Suchen und Einladen funktionieren; Rollenzuordnung, Gruppenänderung und Impersonation werden mit 403 abgelehnt.
- Dokumentation (Freigabe-Workflow, `production-compose.md`, OIDC-Setup) und eine Upgrade-Notiz beschreiben die Umstellung und die Mindestversion Keycloak 26.2. Das Skript bricht bei älteren Versionen ab.
- Der Backend-Code bleibt unverändert; nur die Rechte des Service Accounts ändern sich.

## Capabilities

### New Capabilities

### Modified Capabilities
- `approved-user-onboarding`: Neue Anforderung, dass der Provisioning-Zugang keine Rollen- oder Gruppenzuordnungen, keine Impersonation und keine Delegation erlaubt (Keycloak ≥ 26.2); Löschen bleibt als dokumentiertes Restrisiko.

## Impact

- IdP-Deployment: `idp-deploy/keycloak/setup_keycloak_realm.py` und `services/backend/tests/unit/test_keycloak_setup_script.py`; neuer Integrationstest gegen Keycloak (Testcontainer oder Compose-Service im CI).
- Dokumentation: `docs/features/approval-workflow.md`, `docs/operations/production-compose.md`, `idp-deploy/keycloak/OIDC-SETUP.md`, neue Datei in `docs/operations/release-notes/`.
- Betrieb: Bestehende Installationen führen das Setup-Skript erneut aus oder richten die Permissions in der Admin-Konsole ein. Keycloak 26.2 ist Mindestversion für die dokumentierte Einrichtung; mit älterem externem Keycloak bleibt der bisherige Rollen-Ansatz in Betrieb, erfüllt die neue Anforderung aber nicht (in der Upgrade-Notiz benannt).
- Keine Änderung an Backend-API, Datenbank oder Frontend.
