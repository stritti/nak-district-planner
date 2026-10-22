## 1. Backend

- [ ] 1.1 `app/adapters/idp/keycloak_provisioner.py` und den Keycloak-Zweig in `provisioning.py` entfernen; verifiziert durch `grep -rn keycloak_provisioner services/backend` ohne Treffer.
- [ ] 1.2 `config.py`: alle `idp_provisioning_keycloak_*`-Felder entfernen; Validierung verweigert den Start bei `idp_provisioning_enabled` mit Provider `keycloak` (in jeder Umgebung) mit Verweis auf die Upgrade-Notiz; verifiziert durch Tests in `test_production_guard.py` bzw. Settings-Tests (Start verweigert, Webhook weiterhin erlaubt, deaktiviert erlaubt).
- [ ] 1.3 Tests des Keycloak-Provisioners entfernen bzw. auf Webhook umstellen (`test_misc_low_coverage_modules.py`, `test_provisioning_unit.py`); Freigabe ohne Provider sendet nichts an den IdP; verifiziert durch Unit-Test.
- [ ] 1.4 `.env.example`, `services/backend/.env.example` und `docker-compose.prod.yml` bereinigen; verifiziert durch `grep -rn IDP_PROVISIONING_KEYCLOAK .` ohne Treffer außerhalb von Upgrade-Notizen und archivierten Changes.
- [ ] 1.5 `cd services/backend && uv run pytest tests/unit/ -v && uv run ruff check app tests` laufen grün.

## 2. Realm-Setup

- [ ] 2.1 `setup_keycloak_realm.py`: `REALM_SECURITY_DEFAULTS` setzt `registrationAllowed`, `verifyEmail` und `registrationEmailAsUsername` auf `true`; übrige Vorgaben bleiben; verifiziert durch Unit-Test auf den PUT-Payload.
- [ ] 2.2 `ensure_provisioning_client` durch `remove_provisioning_client` ersetzen, das den Client per `--provisioning-client-id` (Default `nak-planner-provisioning`) löscht, falls vorhanden, und sonst nichts tut; verifiziert durch Unit-Tests (vorhanden → DELETE, fehlt → kein Aufruf).
- [ ] 2.3 `test_keycloak_setup_script.py` angepasst und grün.

## 3. Frontend

- [ ] 3.1 `oidcAuthorization.getAuthorizationUrl` akzeptiert einen optionalen `prompt`, `useOIDC.ts` bietet eine Funktion für den Login mit `prompt=create`; verifiziert durch Unit-Tests auf die erzeugte URL (mit und ohne `prompt`).
- [ ] 3.2 `RegistrationView.vue`: Erfolgsansicht mit Button „Konto anlegen“ und Hinweis auf gleiche E-Mail; angemeldete Benutzer senden ihren Token mit; verifiziert durch `RegistrationView.test.ts`.
- [ ] 3.3 `cd services/frontend && bun run lint && bun run test` (bzw. das Test-Skript aus `package.json`) laufen grün.

## 4. Dokumentation

- [ ] 4.1 `docs/features/approval-workflow.md`, `docs/operations/production-compose.md`, `idp-deploy/keycloak/OIDC-SETUP.md` und `idp-deploy/keycloak/README.md` beschreiben Selbstregistrierung, Auto-Link per verifizierter E-Mail, Bot-Schutz (Proxy-Rate-Limit, optional reCAPTCHA) und den Hinweis zu Webhook-Provisionern; verifiziert durch `npm run docs:build`.
- [ ] 4.2 Upgrade-Notiz in `docs/operations/release-notes/` gemäß `.github/CONTRIBUTING.md` (Betroffen / Vor dem Update / Nach dem Update), inklusive Löschen des Provisioning-Clients, Information ausstehender Bewerber und dem Hinweis, dass sie `679-keycloak-provisioning-service-account.md` (1.5.0) ablöst; verifiziert durch Review.
- [ ] 4.3 Manuelle Abnahme gegen den mitgelieferten Keycloak: neues Konto über „Konto anlegen“ registrieren, E-Mail verifizieren, einloggen; ohne Freigabe `403`, nach Freigabe mit gleicher E-Mail Zugriff (Auto-Link); verifiziert durch Protokoll im PR.
- [ ] 4.4 `npx -y @fission-ai/openspec@1.14.1 validate --all --strict --no-interactive` läuft fehlerfrei.

## Workflow follow-up

- Nach Umsetzung und Merge: `/opsx:archive keycloak-self-registration-onboarding`.
