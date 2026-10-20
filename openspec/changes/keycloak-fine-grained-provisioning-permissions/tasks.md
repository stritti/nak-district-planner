## 1. Scopes gegen echten Keycloak klären

- [ ] 1.1 Keycloak in der Version aus `docker-compose.prod.yml` starten, *Admin Permissions* aktivieren und über den `admin-permissions`-Endpunkt die Scopes des Resource Types *Users* auslesen; verifiziert durch die dokumentierte Scope-Liste im Design.
- [ ] 1.2 Mit einem Service Account ohne `realm-management`-Rollen bestätigen, dass `view` + `manage` über eine Role-Policy Suchen, Anlegen und `execute-actions-email` erlauben, dass eine `reset-password`-Permission auf eine unbenutzte Rolle Passwort-Resets sperrt, ohne `execute-actions-email` zu brechen, und dass Rollenzuordnung, Gruppenänderung, Impersonation und Delegation verweigert werden; Abweichungen in `design.md` und Spec nachtragen; verifiziert durch `npx -y @fission-ai/openspec@1.14.1 validate --all --strict --no-interactive`.

## 2. Setup-Skript

- [ ] 2.1 `setup_keycloak_realm.py` aktiviert Admin Permissions im Realm und bricht bei fehlendem FGAP v2 mit klarer Meldung ab; verifiziert durch Unit-Tests auf Payload und Fehlerpfad.
- [ ] 2.2 Skript legt idempotent die Realm-Rolle `nak-planner-provisioner`, ihre Zuweisung an den Service Account, eine Role-Policy und die Users-Permission mit `view` und `manage` sowie die sperrende `reset-password`-Permission (Rolle `nak-planner-password-reset`, nie zugewiesen) an und bricht ab, wenn Users-Permissions für konkrete Benutzer existieren; verifiziert durch Unit-Tests für Neuanlage und erneuten Lauf.
- [ ] 2.3 Skript entzieht danach `manage-users`/`view-users` (und weitere `realm-management`-Rollen) dem Service Account; verifiziert durch Unit-Test, der die Reihenfolge Permissions vor Entzug prüft.
- [ ] 2.4 `cd services/backend && uv run pytest tests/unit/ -v && uv run ruff check app tests` laufen grün.

## 3. Integrationstest

- [ ] 3.1 Integrationstest mit Keycloak-Container, der das Setup-Skript ausführt und alle Szenarien der Spec mit dem Client-Credentials-Token prüft (erlaubt: Suchen, Anlegen, Einladung, auch Suche nach bestehendem Benutzer; 403: Passwort setzen, Rollenzuordnung, Gruppenänderung, Impersonation, Anlegen einer Admin-Permission); verifiziert durch grünen Testlauf lokal.
- [ ] 3.2 Eigener CI-Job für diesen Test; verifiziert durch grünen Job im PR.

## 4. Dokumentation

- [ ] 4.1 `docs/features/approval-workflow.md`, `docs/operations/production-compose.md` und `idp-deploy/keycloak/OIDC-SETUP.md` beschreiben FGAP v2, die manuelle Einrichtung in der Admin-Konsole, die Mindestversion 26.2 und die Voraussetzung keiner benutzerspezifischen Users-Permissions und das Restrisiko Löschen/Bearbeiten samt Empfehlung, Keycloak-Admin-Events zu aktivieren; verifiziert durch `npm run docs:build`.
- [ ] 4.2 Upgrade-Notiz in `docs/operations/release-notes/` gemäß `.github/CONTRIBUTING.md` (Betroffen / Vor dem Update / Nach dem Update); verifiziert durch Review.
- [ ] 4.3 `npx -y @fission-ai/openspec@1.14.1 validate --all --strict --no-interactive` läuft fehlerfrei.

## Workflow follow-up

- Nach Umsetzung und Merge: `/opsx:archive keycloak-fine-grained-provisioning-permissions`.
