## Why

`nakctl` (Change `production-admin-scripts`) deckt den laufenden Betrieb ab. Zwei Lücken bleiben: Vor dem ersten Start fehlt eine Diagnose, warum eine Installation nicht läuft (fehlende Werkzeuge, unvollständige `.env`, DNS, belegte Ports). `status` und `check` setzen einen laufenden Stack voraus und nennen keine Behebung. Die Erstinstallation verlangt außerdem, vier `.env`-Dateien zu kopieren, sechs Secrets zu erzeugen, das Keycloak-Datenbankpasswort an zwei Stellen gleich zu halten und Rechte zu setzen. Das ist mühsam und fehleranfällig, und von Hand erzeugte Secrets landen leicht in der Shell-History.

## What Changes

- **`nakctl doctor`** (nur lesend): prüft Werkzeuge (bash, Docker-Daemon, Compose ≥ 2.20, Python ≥ 3.11, openssl, gpg mit dem Schlüssel aus `BACKUP_ENCRYPT_KEY`), Konfiguration (`.env`, `COMPOSE_FILE` und `docker compose config`, `APP_ENV=production`, `APP_VERSION` als Release-Tag) und Netz (DNS von `APP_HOST`/`AUTH_HOST`, Ports 80/443 nicht fremd belegt, wenn der Stack Traefik mitbringt). Danach führt es `check all` aus. Jeder Befund kommt mit einem konkreten Hinweis zur Behebung. `--offline` lässt DNS und Zertifikate aus, `--skip-checks` das `check all`.
- **`nakctl setup init`**: legt fehlende `.env`, `.env.db`, `.env.keycloak` und `.env.keycloak-db` aus den Vorlagen mit Rechten 0600 an, erzeugt zufällige, URL-sichere Secrets, hält `KC_DB_PASSWORD` und das Keycloak-`POSTGRES_PASSWORD` gleich, passt `DATABASE_URL`/`VALKEY_URL` an und setzt `APP_ENV=production`, `COMPOSE_FILE` sowie optional `APP_HOST`, `AUTH_HOST`, `APP_VERSION` und `BACKUP_ENCRYPT_KEY`. Vorhandene Dateien bleiben unverändert, Secrets werden nie ausgegeben. Am Ende stehen die manuellen nächsten Schritte.

## Capabilities

### New Capabilities
- keine

### Modified Capabilities
- `operations-tooling`: zwei zusätzliche Bereiche `doctor` und `setup` (Requirements werden ergänzt).

## Impact

- Geänderte Dateien: `scripts/ops/nakctl`, `scripts/ops/nakops.py` (Unterbefehl `init-env`), Tests `scripts/ops/test_nakctl.py` und `scripts/ops/test_nakops.py`.
- Keine Änderung an Backend, Frontend, Datenbankschema oder Compose-Dateien.
- Dokumentation (VitePress): `docs/operations/admin-scripts.md` (neue Abschnitte Doctor und Setup), `docs/operations/production-compose.md` (Einrichtung mit `setup init`, Prüfen mit `doctor`). Der Demo-Bezirk ist nicht betroffen.

## Non-Goals

- Keine automatische Keycloak-Einrichtung: Realm und Client bleiben bei `idp-deploy/keycloak/setup_keycloak_realm.py` oder der Konsole, weil das OIDC-Secret erst danach existiert.
- Kein automatischer Start des Stacks und keine Migration durch `setup`; dafür gibt es `docker compose up` und `deploy update`.
- Kein Überschreiben oder Rotieren vorhandener Secrets.
- Kein Prüfen externer Dienste (SMTP-Versand, OIDC-Login) durch `doctor`.
