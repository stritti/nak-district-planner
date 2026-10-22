## Why

Das Backend legt bei einer Freigabe optional Benutzer in Keycloak an und verschickt Einladungen. Dafür hält es das Secret eines Service Accounts mit `manage-users`. Die Prüfung im Change `keycloak-fine-grained-provisioning-permissions` (PR #681) hat gezeigt, dass auch feingranulare Admin-Berechtigungen (FGAP v2) eine Kontoübernahme mit diesem Secret nicht verhindern: Keycloak 26.8.1 bindet E-Mail-Änderung plus `execute-actions-email`, das Löschen von OTP-/WebAuthn-Credentials und das Verknüpfen externer Identitäten allein an den Scope `manage`. Ein gestohlenes Backend-Secret würde damit jedes Konto übernehmen können, auch Bezirksadmins mit OTP.

Die App braucht diese Rechte nicht: Ein Keycloak-Konto ohne App-Membership gewährt keinen Zugriff, und die App verknüpft freigegebene Registrierungen schon heute beim ersten Login über eine verifizierte E-Mail (`user-onboarding`, #461). Stephan hat am 2026-10-22 entschieden, die Provisionierung durch das Backend aufzugeben. Dieser Change ersetzt den nie umgesetzten FGAP-Change.

## What Changes

- **BREAKING** Der Keycloak-Provisioner im Backend entfällt mit allen `IDP_PROVISIONING_KEYCLOAK_*`-Einstellungen. Ist `IDP_PROVISIONING_PROVIDER=keycloak` gesetzt, verweigert die App den Start mit einem Hinweis auf die Upgrade-Notiz. Der Webhook-Provider bleibt unverändert.
- Benutzer legen ihr Keycloak-Konto selbst an. Das Realm-Setup-Skript aktiviert die Selbstregistrierung mit E-Mail-Verifizierung (bisher deaktiviert) und lässt Brute-Force-Schutz, Passwort-Policy und die übrigen Realm-Vorgaben unverändert.
- Das Skript legt keinen Provisioning-Client mehr an und löscht einen vorhandenen `nak-planner-provisioning`-Client, damit sein Secret ungültig wird.
- Die Registrierungsseite der App bietet nach dem Absenden „Konto anlegen“ an (OIDC-Login mit `prompt=create`) und erklärt, dass die E-Mail-Adresse übereinstimmen muss. Ist der Benutzer schon angemeldet, sendet sie den Token mit, sodass die Registrierung direkt verknüpft wird.
- Doku (Freigabe-Workflow, `production-compose.md`, OIDC-Setup, `.env.example`) und eine Upgrade-Notiz beschreiben den neuen Ablauf, Bot-Schutz für die Registrierung (Rate-Limit am Reverse Proxy, optional reCAPTCHA in Keycloak) und die Migration.
- Der FGAP-Change `keycloak-fine-grained-provisioning-permissions` wird ohne Umsetzung entfernt.

## Capabilities

### New Capabilities

### Modified Capabilities
- `approved-user-onboarding`: Die Anforderungen zum Keycloak-Service-Account und zu Einladungslinks entfallen; neu sind die Anforderungen, dass das Backend kein Keycloak-Admin-Secret hält und dass Konten per Selbstregistrierung mit verifizierter E-Mail entstehen.

## Impact

- Backend: `app/adapters/idp/keycloak_provisioner.py` und Tests entfallen; `provisioning.py`, `config.py` (Einstellungen, Production Guard) und `.env.example`-Dateien werden angepasst. Die Spalten `idp_provision_*` bleiben für den Webhook-Provider und bestehende Datensätze erhalten; keine Migration.
- IdP-Deployment: `idp-deploy/keycloak/setup_keycloak_realm.py` und `test_keycloak_setup_script.py`.
- Frontend: `RegistrationView.vue`, `useOIDC.ts` (Login mit `prompt=create`), Tests.
- Betrieb: Installationen mit Keycloak-Provisioning entfernen die Einstellungen, führen das Setup-Skript erneut aus und informieren ausstehende Bewerber, dass sie ihr Konto selbst anlegen.
