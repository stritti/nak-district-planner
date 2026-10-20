## 1. Settings und Produktions-Guard

- [x] 1.1 In `app/config.py` `idp_provisioning_keycloak_client_id`, `_client_secret`, `_invite_lifespan_seconds` (`Field(default=259200, ge=3600, le=604800)`) und `_invite_redirect_uri` ergänzen und die Admin-Username/Password-Settings entfernen; verifiziert durch Config-Unit-Tests für Default und Grenzwerte 3599/604801.
- [x] 1.2 Produktions-Guard: fehlende Client-Credentials, gesetzte `IDP_PROVISIONING_KEYCLOAK_ADMIN_*` und eine Redirect-URI ohne `https://` ablehnen; verifiziert durch negative Unit-Tests je Fall.
- [x] 1.3 `.env.example` auf die neuen Variablen umstellen; verifiziert durch `grep` ohne Treffer für `KEYCLOAK_ADMIN_USERNAME` in `.env.example`.

## 2. Keycloak-Provisioner

- [x] 2.1 `_get_admin_token` auf `client_credentials` gegen `/realms/{realm}/protocol/openid-connect/token` umstellen und `get_idp_provisioner()` anpassen; verifiziert durch Unit-Test, der URL und Formdaten prüft und dass kein Request an `master` geht.
- [x] 2.2 `_trigger_invite` sendet `lifespan` immer und `client_id`/`redirect_uri` nur bei konfigurierter Redirect-URI; verifiziert durch Unit-Tests für beide Fälle.
- [x] 2.3 Fehlertexte enthalten nur HTTP-Status, nie Secret oder Token; verifiziert durch Unit-Test mit abgelehntem Token-Request, der das Secret im gespeicherten `idp_provision_error` ausschließt.
- [x] 2.4 `uv run pytest tests/unit/ -v` und `make lint` laufen grün.

## 3. Realm-Setup-Skript

- [x] 3.1 `setup_keycloak_realm.py` setzt die sicheren Realm-Defaults (auch bei bestehendem Realm per `PUT`); verifiziert durch Erweiterung von `tests/unit/test_keycloak_setup_script.py`, die das Payload prüft.
- [x] 3.2 Skript legt den Confidential Client `nak-planner-provisioning` mit Service Account und nur `manage-users`/`view-users` an und gibt das Secret einmalig aus; verifiziert durch Unit-Test auf Client-Payload und Rollen-Zuweisung.

## 4. Dokumentation

- [x] 4.1 `docs/features/approval-workflow.md` und `idp-deploy/keycloak/OIDC-SETUP.md` beschreiben Service Account, Einladungslaufzeit, Rücksprung und Realm-SMTP (gleiches Relay wie die App); verifiziert durch `npm run docs:build` im Repo-Root ohne tote Links.
- [x] 4.2 `docs/operations/production-compose.md` (Abschnitt Keycloak/IdP-Provisioning) erhält Migrationsschritte, Secret-Rotation, SMTP-Test im Realm und die Empfehlung OTP/Passkey für `DISTRICT_ADMIN`; verifiziert durch Review.
- [x] 4.3 `npx -y @fission-ai/openspec@1.14.1 validate --all` läuft fehlerfrei.

## Workflow follow-up

- Nach Umsetzung und Merge: `/opsx:archive harden-keycloak-provisioning`, damit die Baseline-Spec `approved-user-onboarding` aktualisiert wird.
