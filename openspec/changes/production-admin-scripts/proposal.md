## Why

Der produktive Betrieb verlangt heute viele einzelne, von Hand zusammengesetzte Kommandos: `valkey-cli` mit Passwort aus `.env`, `docker compose logs` mit `grep`, `scripts/backup.sh` und `scripts/restore.sh` mit wechselnden Umgebungsvariablen. Das ist fehleranfällig. Ein falsches `FLUSHALL` löscht neben der Celery-Warteschlange auch Ergebnisse und Rate-Limit-Zähler, ein Passwort auf der Kommandozeile landet in der Shell-History, und Logs werden mit Export-Tokens oder E-Mail-Adressen in Tickets kopiert. Betreiber brauchen einen kleinen, sicheren und dokumentierten Werkzeugkasten für die wiederkehrenden Aufgaben.

## What Changes

- Neuer Einstiegspunkt `scripts/ops/nakctl` (Bash) mit Unterbefehlen; er liest `COMPOSE_FILE` und `.env` wie die bestehenden Skripte und läuft auf dem Produktionsserver im Release-Checkout.
- **Warteschlange (Valkey/Celery):** `queue status` (Länge der Celery-Queue, unbestätigte Nachrichten, Anzahl Ergebnis-Schlüssel), `queue inspect` (Histogramm der Task-Namen, **ohne** Argumente), `queue purge` (leert nur die Celery-Warteschlange nach Bestätigung, warnt vor nicht idempotenten Mail-Tasks), `queue purge-results` (entfernt nur `celery-task-meta-*`). Kein `FLUSHALL`/`FLUSHDB`.
- **Backup:** `backup create`, `backup list` (Alter, Größe, Rollenarchiv vorhanden), `backup verify <datei>` und `backup restore <datei>` als dünne Hüllen um `scripts/backup.sh` und `scripts/restore.sh`; `backup create --keycloak` sichert zusätzlich die Keycloak-Datenbank.
- **Logs:** `logs analyze [--since 24h] [--service …] [--json]` fasst Fehler und Warnungen je Dienst, HTTP-5xx, fehlgeschlagene und wiederholte Celery-Tasks, Rate-Limiter-Fallbacks und Audit-Schreibfehler zusammen. `logs export` schreibt einen redigierten Auszug für Tickets. Export-Tokens, Bearer-Tokens, Passwörter und E-Mail-Adressen werden immer maskiert.
- **Zustand:** `status` zeigt Container-Zustand, `/health`, Alembic-Stand gegen Image-Head, Alter des letzten Backups und Plattenbelegung der Volumes.
- Gemeinsame Regeln: `--dry-run` für jeden ändernden Befehl, Bestätigung oder `--yes` für destruktive Befehle, keine Secrets in Ausgabe oder Prozessargumenten, definierte Exit-Codes für Cron und Monitoring.

## Capabilities

### New Capabilities
- `operations-tooling`: Hilfsskripte für den produktiven Betrieb (Warteschlange, Backup, Log-Analyse, Zustandsprüfung) und ihre Sicherheitsregeln.

### Modified Capabilities
- keine (`production-deployment` behält `backup.sh`/`restore.sh` unverändert; die neuen Befehle bauen darauf auf)

## Impact

- Neue Dateien: `scripts/ops/nakctl`, `scripts/ops/lib.sh`, `scripts/ops/analyze_logs.py` (nur Python-Standardbibliothek), Tests `scripts/ops/test_analyze_logs.py` und Shell-Tests für `nakctl`.
- CI: ShellCheck für `scripts/ops/` und die Python-Tests im bestehenden Skript-Testlauf.
- Keine Änderung an Backend, Frontend, Datenbankschema oder Compose-Dateien.
- Dokumentation (VitePress): neue Seite `docs/operations/admin-scripts.md`; Verweise in `docs/operations/production-runbook.md` (Abschnitte Backup/Restore, Monitoring, Celery-Diagnose) und `docs/operations/production-compose.md` (Backup); Navigation in `docs/.vitepress/config.*`. Der Demo-Bezirk ist nicht betroffen.

## Non-Goals

- Keine Web-Oberfläche oder API-Endpunkte für Administration.
- Kein Ersatz für zentrales Logging, Monitoring oder Alerting (OpenTelemetry bleibt der Weg dafür).
- Kein automatisches Wiedereinspielen gelöschter Celery-Nachrichten und keine Off-Site-Kopie der Backups (bleibt Aufgabe des Betreibers, z. B. per Cron und `rsync`).
- Kein Kubernetes- oder Multi-Host-Betrieb.
