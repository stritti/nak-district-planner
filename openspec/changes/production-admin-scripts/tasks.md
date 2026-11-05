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

## 4. Logs und Status

- [ ] 4.1 `scripts/ops/analyze_logs.py`: Parsing, Zählung, Normalisierung, Musterliste, Redaktion, `--json`, `--fail-on-errors`
- [ ] 4.2 `logs analyze` und `logs export` (Datei mit 0600)
- [ ] 4.3 `status` (Container, `/health`, Alembic-Stand, Volumes, Backup-Alter)

## 5. Tests und CI

- [ ] 5.1 Unit-Tests `scripts/ops/test_analyze_logs.py` mit Beispielzeilen und Redaktions-Negativtests
- [ ] 5.2 Shell-Tests für Argumentprüfung, `--dry-run` und Exit-Codes mit gestubbtem `docker`
- [ ] 5.3 CI: ShellCheck für `scripts/ops/`, Python-Tests, Integrationstest `queue status`/`queue purge` gegen Valkey mit Passwort

## 6. Dokumentation

- [ ] 6.1 Neue Seite `docs/operations/admin-scripts.md` (Befehle, Beispiele, Cron-Beispiele, Exit-Codes, Sicherheitsregeln)
- [ ] 6.2 Verweise in `docs/operations/production-runbook.md` (Backup/Restore, Monitoring, Celery-Diagnose) und `docs/operations/production-compose.md` (Backup)
- [ ] 6.3 Navigation in der VitePress-Konfiguration ergänzen; `scripts/verify-docs.mjs` grün
