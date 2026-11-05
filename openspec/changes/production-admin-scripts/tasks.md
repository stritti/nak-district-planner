## 1. Grundgerüst

- [x] 1.1 `scripts/ops/lib.sh` mit Deploy-Verzeichnis, `.env`-Lesen ohne `source`, Compose-Aufruf, Bestätigung, `--dry-run`/`--yes`, Exit-Codes und Protokollzeile
- [x] 1.2 `scripts/ops/nakctl` mit Dispatcher, Parameter-Hilfe (`--help`/`-h` je Bereich, `nakctl help <bereich>`, Beispiele) und SPDX-Header

## 2. Warteschlange

- [x] 2.1 `queue status` (Queue-Länge, unacked, Ergebnis-Schlüssel per SCAN, Worker-Ping)
- [x] 2.2 `queue inspect` mit Task-Namen-Histogramm ohne Argumente
- [x] 2.3 `queue purge` mit Histogramm, Mail-Warnung, Bestätigung `LEEREN`, `--include-unacked` nur bei gestoppten Workern
- [x] 2.4 `queue purge-results` per SCAN/UNLINK; Test, dass kein FLUSHALL/FLUSHDB verwendet wird

## 3. Backup

- [x] 3.1 `backup create` (inkl. `--keycloak`), `verify`, `restore` als Hüllen um `backup.sh`/`restore.sh`
- [x] 3.2 `backup list` mit Paarprüfung und `--max-age-hours`
- [x] 3.3 `BACKUP_POST_HOOK` mit Rechteprüfung und Beispiel `scripts/ops/examples/backup-post-hook-rsync.sh`

## 4. Logs und Status

- [x] 4.1 `scripts/ops/nakops.py`: Parsing, Zählung, Normalisierung, Musterliste, Redaktion, `--json`, `--fail-on-errors`
- [x] 4.2 `logs analyze` und `logs export` (Datei mit 0600)
- [x] 4.3 `status` (Container, `/health`, Alembic-Stand, Volumes, Backup-Alter)
- [x] 4.4 `check certs`, `check disk`, `check secrets` und `check all`

## 5. Deploy, Datenbank, Superadmin, Aufräumen

- [x] 5.1 `deploy update <version>` mit Manifest-Prüfung, Backup, Migration und Health-Wartezeit
- [x] 5.2 `deploy rollback` mit Schema-Prüfung gegen das alte Image
- [x] 5.3 `db stats` mit gekürzten, literalfreien Abfragetexten und `db vacuum`
- [x] 5.4 `superadmin list` und `superadmin set-sub` mit psql-Variablen
- [x] 5.5 `cleanup images` (laufende und vorherige Version bleiben)

## 6. Tests und CI

- [x] 6.1 Unit-Tests `scripts/ops/test_nakops.py` mit Beispielzeilen und Redaktions-Negativtests
- [x] 6.2 Verhaltenstests `scripts/ops/test_nakctl.py` für Argumentprüfung, Hilfe, `--dry-run` und Exit-Codes mit gestubbtem `docker`
- [x] 6.3 CI (`.github/workflows/ops-scripts.yml`): ShellCheck für `scripts/ops/`, Python-Tests, Integrationstest `queue status`/`queue purge` gegen Valkey mit Passwort sowie `db stats` und `superadmin set-sub` gegen PostgreSQL

## 7. Dokumentation

- [x] 7.1 Neue Seite `docs/operations/admin-scripts.md` (Befehle, Beispiele, Cron-Beispiele, Exit-Codes, Sicherheitsregeln)
- [x] 7.2 Verweise in `docs/operations/production-runbook.md` (Superadmin-Bootstrap, Deployment, Rollback, Backup/Restore, Monitoring, Celery-Diagnose) und `docs/operations/production-compose.md` (Backup)
- [x] 7.3 Navigation in der VitePress-Konfiguration ergänzen; `scripts/verify-docs.mjs` grün
