## 1. Grundgerüst

- [ ] 1.1 `scripts/ops/lib.sh` mit Deploy-Verzeichnis, `.env`-Lesen ohne `source`, Compose-Aufruf, Bestätigung, `--dry-run`/`--yes`, Exit-Codes und Protokollzeile
- [ ] 1.2 `scripts/ops/nakctl` mit Dispatcher, `--help` je Bereich und SPDX-Header

## 2. Warteschlange

- [ ] 2.1 `queue status` (Queue-Länge, unacked, Ergebnis-Schlüssel per SCAN, Worker-Ping)
- [ ] 2.2 `queue inspect` mit Task-Namen-Histogramm ohne Argumente
- [ ] 2.3 `queue purge` mit Histogramm, Mail-Warnung, Bestätigung `LEEREN`, `--include-unacked` nur bei gestoppten Workern
- [ ] 2.4 `queue purge-results` per SCAN/UNLINK; Test, dass kein FLUSHALL/FLUSHDB verwendet wird

## 3. Backup

- [ ] 3.1 `backup create` (inkl. `--keycloak`), `verify`, `restore` als Hüllen um `backup.sh`/`restore.sh`
- [ ] 3.2 `backup list` mit Paarprüfung und `--max-age-hours`
- [ ] 3.3 `BACKUP_POST_HOOK` mit Rechteprüfung und Beispiel `scripts/ops/examples/backup-post-hook-rsync.sh`

## 4. Logs und Status

- [ ] 4.1 `scripts/ops/analyze_logs.py`: Parsing, Zählung, Normalisierung, Musterliste, Redaktion, `--json`, `--fail-on-errors`
- [ ] 4.2 `logs analyze` und `logs export` (Datei mit 0600)
- [ ] 4.3 `status` (Container, `/health`, Alembic-Stand, Volumes, Backup-Alter)
- [ ] 4.4 `check certs`, `check disk`, `check secrets` und `check all`

## 5. Deploy, Datenbank, Superadmin, Aufräumen

- [ ] 5.1 `deploy update <version>` mit Manifest-Prüfung, Backup, Migration und Health-Wartezeit
- [ ] 5.2 `deploy rollback` mit Schema-Prüfung gegen das alte Image
- [ ] 5.3 `db stats` mit gekürzten, literalfreien Abfragetexten und `db vacuum`
- [ ] 5.4 `superadmin list` und `superadmin set-sub` mit psql-Variablen
- [ ] 5.5 `cleanup images` (laufende und vorherige Version bleiben)

## 6. Tests und CI

- [ ] 6.1 Unit-Tests `scripts/ops/test_analyze_logs.py` mit Beispielzeilen und Redaktions-Negativtests
- [ ] 6.2 Shell-Tests für Argumentprüfung, `--dry-run` und Exit-Codes mit gestubbtem `docker`
- [ ] 6.3 CI: ShellCheck für `scripts/ops/`, Python-Tests, Integrationstest `queue status`/`queue purge` gegen Valkey mit Passwort sowie `db stats` und `superadmin set-sub` gegen PostgreSQL

## 7. Dokumentation

- [ ] 7.1 Neue Seite `docs/operations/admin-scripts.md` (Befehle, Beispiele, Cron-Beispiele, Exit-Codes, Sicherheitsregeln)
- [ ] 7.2 Verweise in `docs/operations/production-runbook.md` (Superadmin-Bootstrap, Deployment, Rollback, Backup/Restore, Monitoring, Celery-Diagnose) und `docs/operations/production-compose.md` (Backup)
- [ ] 7.3 Navigation in der VitePress-Konfiguration ergänzen; `scripts/verify-docs.mjs` grün
