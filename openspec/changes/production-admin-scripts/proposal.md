## Why

Der produktive Betrieb verlangt heute viele einzelne, von Hand zusammengesetzte Kommandos: `valkey-cli` mit Passwort aus `.env`, `docker compose logs` mit `grep`, `scripts/backup.sh` und `scripts/restore.sh` mit wechselnden Umgebungsvariablen. Das ist fehleranfällig. Ein falsches `FLUSHALL` löscht neben der Celery-Warteschlange auch Ergebnisse und Rate-Limit-Zähler, ein Passwort auf der Kommandozeile landet in der Shell-History, und Logs werden mit Export-Tokens oder E-Mail-Adressen in Tickets kopiert. Betreiber brauchen einen kleinen, sicheren und dokumentierten Werkzeugkasten für die wiederkehrenden Aufgaben.

## What Changes

- Neuer Einstiegspunkt `scripts/ops/nakctl` (Bash) mit Unterbefehlen; er liest `COMPOSE_FILE` und `.env` wie die bestehenden Skripte und läuft auf dem Produktionsserver im Release-Checkout.
- **Warteschlange (Valkey/Celery):** `queue status` (Länge der Celery-Queue, unbestätigte Nachrichten, Anzahl Ergebnis-Schlüssel), `queue inspect` (Histogramm der Task-Namen, **ohne** Argumente), `queue purge` (leert nur die Celery-Warteschlange nach Bestätigung, warnt vor nicht idempotenten Mail-Tasks), `queue purge-results` (entfernt nur `celery-task-meta-*`). Kein `FLUSHALL`/`FLUSHDB`.
- **Backup:** `backup create`, `backup list` (Alter, Größe, Rollenarchiv vorhanden), `backup verify <datei>` und `backup restore <datei>` als dünne Hüllen um `scripts/backup.sh` und `scripts/restore.sh`; `backup create --keycloak` sichert zusätzlich die Keycloak-Datenbank.
- **Logs:** `logs analyze [--since 24h] [--service …] [--json]` fasst Fehler und Warnungen je Dienst, HTTP-5xx, fehlgeschlagene und wiederholte Celery-Tasks, Rate-Limiter-Fallbacks und Audit-Schreibfehler zusammen. `logs export` schreibt einen redigierten Auszug für Tickets. Export-Tokens, Bearer-Tokens, Passwörter und E-Mail-Adressen werden immer maskiert.
- **Zustand:** `status` zeigt Container-Zustand, `/health`, Alembic-Stand gegen Image-Head, Alter des letzten Backups und Plattenbelegung der Volumes.
- **Prüfungen:** `check certs` (Ablauf der TLS-Zertifikate von App- und Keycloak-Host), `check disk` (freier Platz auf dem Host und in den Volumes mit Schwellwert), `check secrets` (Rechte 0600 auf `.env`-Dateien, Pflichtwerte gesetzt, keine Beispielwerte; Werte werden nie ausgegeben).
- **Deploy:** `deploy update <version>` (Release-Tag prüfen, Backup, Images ziehen, Migration, Start, Warten auf `/health`) und `deploy rollback` auf die zuvor laufende Version; bricht ab, wenn die Datenbank bereits neuer migriert ist, und verweist dann auf Restore oder Downgrade.
- **Datenbank:** `db stats` (Größe je Tabelle, Verbindungen, lange Abfragen, Sperren, letzter Autovacuum) und `db vacuum` (`VACUUM (ANALYZE)` nach Bestätigung).
- **Superadmin-Wiederherstellung:** `superadmin list` und `superadmin set-sub <sub>` kapseln das SQL aus Runbook Abschnitt 2.3 für einen Realm- oder IdP-Wechsel.
- **Aufräumen:** `cleanup images` entfernt lokale Images älterer App-Versionen und behält laufende und vorherige Version.
- **Off-Site-Hook:** Ist `BACKUP_POST_HOOK` gesetzt, ruft `backup create` nach einem vollständigen Backup dieses Betreiber-Skript mit den Archivpfaden auf (z. B. für `rsync` oder `rclone`).
- Alle Befehle sind Shell-Skripte unter `scripts/ops/`; nur die Log-Auswertung nutzt ein Python-Skript mit Standardbibliothek. Es gibt keine zusätzlichen `make`-Ziele.
- Gemeinsame Regeln: `--dry-run` für jeden ändernden Befehl, Bestätigung oder `--yes` für destruktive Befehle, keine Secrets in Ausgabe oder Prozessargumenten, definierte Exit-Codes für Cron und Monitoring.

## Capabilities

### New Capabilities
- `operations-tooling`: Hilfsskripte für den produktiven Betrieb (Warteschlange, Backup, Log-Analyse, Zustand und Prüfungen, Deploy und Rollback, Datenbankwartung, Superadmin-Wiederherstellung, Aufräumen) und ihre Sicherheitsregeln.

### Modified Capabilities
- keine (`production-deployment` behält `backup.sh`/`restore.sh` unverändert; die neuen Befehle bauen darauf auf)

## Impact

- Neue Dateien: `scripts/ops/nakctl`, `scripts/ops/lib.sh`, `scripts/ops/nakops.py` (nur Python-Standardbibliothek), `scripts/ops/examples/backup-post-hook-rsync.sh`, Tests `scripts/ops/test_nakops.py` und `scripts/ops/test_nakctl.py`.
- CI: neuer Workflow `ops-scripts` mit ShellCheck und den Tests gegen Valkey/Redis und PostgreSQL.
- Keine Änderung an Backend, Frontend, Datenbankschema oder Compose-Dateien.
- Dokumentation (VitePress): neue Seite `docs/operations/admin-scripts.md`; Verweise in `docs/operations/production-runbook.md` (Abschnitte Superadmin-Bootstrap, Deployment, Rollback, Backup/Restore, Monitoring, Celery-Diagnose) und `docs/operations/production-compose.md` (Backup); Navigation in `docs/.vitepress/config.*`. Der Demo-Bezirk ist nicht betroffen.

## Non-Goals

- Keine Web-Oberfläche oder API-Endpunkte für Administration.
- Kein Ersatz für zentrales Logging, Monitoring oder Alerting (OpenTelemetry bleibt der Weg dafür).
- Kein automatisches Wiedereinspielen gelöschter Celery-Nachrichten. Die Off-Site-Kopie selbst bleibt ein Betreiber-Skript hinter `BACKUP_POST_HOOK`; das Repository liefert nur ein Beispiel.
- Keine Rotation von `ENCRYPTION_KEY`: Die Anwendung kennt nur einen Fernet-Schlüssel, eine Rotation braucht Änderungen im Backend und ist ein eigener Change. Passwortwechsel für Valkey und Datenbank bleiben vorerst dokumentierte Handgriffe.
- Keine Benutzer- oder Rollenverwaltung in Keycloak: Dafür gibt es die Keycloak-Konsole und die Benutzerverwaltung der Anwendung; ein Keycloak-spezifisches Skript widerspräche der IdP-unabhängigen Anmeldung.
- Kein automatisches Downgrade der Datenbank beim Rollback.
- Kein Kubernetes- oder Multi-Host-Betrieb.
