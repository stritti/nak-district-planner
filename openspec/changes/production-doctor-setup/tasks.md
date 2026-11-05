## 1. Doctor

- [x] 1.1 `nakctl doctor` mit Werkzeugen, Konfiguration, Netz, `check all` und Hinweisen je Befund; `--offline`, `--skip-checks`
- [x] 1.2 Tests: gesunde Installation, Docker nicht erreichbar (Exit 3), Konfigurationsbefunde mit Hinweis, fehlender GPG-Schlüssel und alte Compose-Version, belegter Port

## 2. Setup

- [x] 2.1 `nakops init-env`: Vorlagen kopieren (0600, `O_EXCL`), Secrets erzeugen, Keycloak-Passwort abgleichen, URLs anpassen, Einstellungen setzen
- [x] 2.2 `nakctl setup init` mit Eingabeprüfung, `--dry-run`, Protokollzeile und nächsten Schritten
- [x] 2.3 Tests: neue Dateien und Rechte, keine Secrets in der Ausgabe, vorhandene Dateien unverändert, Dry-Run, ungültige Eingaben, fehlende Vorlagen

## 3. Dokumentation

- [x] 3.1 `docs/operations/admin-scripts.md`: Abschnitte Doctor und Setup
- [x] 3.2 `docs/operations/production-compose.md`: Einrichtung mit `setup init`, Prüfen mit `doctor`
