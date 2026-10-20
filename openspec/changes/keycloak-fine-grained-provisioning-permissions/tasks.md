## 1. Scopes gegen echten Keycloak klären

- [ ] 1.1 Keycloak in der Version aus `docker-compose.prod.yml` starten, *Admin Permissions* aktivieren und über den `admin-permissions`-Endpunkt die Scopes des Resource Types *Users* auslesen; verifiziert durch die dokumentierte Scope-Liste im Design.
- [ ] 1.2 Mit einem Service Account ohne `realm-management`-Rollen ermitteln, welche Scopes Suchen, Anlegen und `execute-actions-email` erlauben und ob Löschen dabei ausgeschlossen werden kann; Ergebnis in `design.md` nachtragen und Spec-Szenarien bei Bedarf anpassen; verifiziert durch `npx -y @fission-ai/openspec@1.14.1 validate --all --strict --no-interactive`.

## 2. Setup-Skript

- [ ] 2.1 `setup_keycloak_realm.py` aktiviert Admin Permissions im Realm und bricht bei fehlendem FGAP v2 mit klarer Meldung ab; verifiziert durch Unit-Tests auf Payload und Fehlerpfad.
- [ ] 2.2 Skript legt idempotent eine Client-Policy für `nak-planner-provisioning` und die Users-Permission mit den in 1.2 ermittelten Scopes an; verifiziert durch Unit-Tests für Neuanlage und erneuten Lauf.
- [ ] 2.3 Skript entzieht danach `manage-users`/`view-users` (und weitere `realm-management`-Rollen) dem Service Account; verifiziert durch Unit-Test, der die Reihenfolge Permissions vor Entzug prüft.
- [ ] 2.4 `cd services/backend && uv run pytest tests/unit/ -v && uv run ruff check app tests` laufen grün.

## 3. Integrationstest

- [ ] 3.1 Integrationstest mit Keycloak-Container, der das Setup-Skript ausführt und alle Szenarien der Spec mit dem Client-Credentials-Token prüft (erlaubt: Suchen, Anlegen, Einladung; 403: Rollenzuordnung, Gruppenänderung, Löschen); verifiziert durch grünen Testlauf lokal.
- [ ] 3.2 Eigener CI-Job für diesen Test; verifiziert durch grünen Job im PR.

## 4. Dokumentation

- [ ] 4.1 `docs/features/approval-workflow.md`, `docs/operations/production-compose.md` und `idp-deploy/keycloak/OIDC-SETUP.md` beschreiben FGAP v2, die manuelle Einrichtung in der Admin-Konsole und den Fallback für Keycloak < 26.2; verifiziert durch `npm run docs:build`.
- [ ] 4.2 Upgrade-Notiz in `docs/operations/release-notes/` gemäß `.github/CONTRIBUTING.md` (Betroffen / Vor dem Update / Nach dem Update); verifiziert durch Review.
- [ ] 4.3 `npx -y @fission-ai/openspec@1.14.1 validate --all --strict --no-interactive` läuft fehlerfrei.

## Workflow follow-up

- Nach Umsetzung und Merge: `/opsx:archive keycloak-fine-grained-provisioning-permissions`.
