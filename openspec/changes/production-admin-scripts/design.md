## Context

- Produktion läuft laut `docs/operations/production-compose.md` als Release-Checkout auf einem Docker-Host; `COMPOSE_FILE=docker-compose.prod.yml` steht in `.env`. Auf dem Server sind Docker Compose, Bash und Python 3 vorhanden (`scripts/check_ics_canary_logs.py` setzt das schon voraus), PostgreSQL- und Valkey-Clients nur in den Containern.
- Celery nutzt Valkey als Broker und Result-Backend (`app/celery_app.py`, Requirement „Reliable Celery transport“). Standard-Queue ist die Liste `celery`; unbestätigte Nachrichten liegen in `unacked`/`unacked_index`, Ergebnisse in `celery-task-meta-*`. Dieselbe Valkey-Instanz hält die Rate-Limit-Zähler.
- Valkey verlangt ein Passwort (`VALKEY_PASSWORD`); der Healthcheck übergibt es über `REDISCLI_AUTH`.
- `scripts/backup.sh` erzeugt verschlüsselte Datenbank- und Rollenarchive, `scripts/restore.sh` prüft mit `--dry-run` und stellt nach Bestätigung wieder her.
- Backend-Logs haben das Format `%(asctime)s %(levelname)s [%(name)s] %(message)s`; Compose schreibt sie per `json-file` mit Rotation (10 MB × 5).
- Celery-Task-Argumente können personenbezogene Daten enthalten (Mail-Empfänger, Namen).

## Goals / Non-Goals

**Goals:** Ein Einstiegspunkt mit einheitlicher Bedienung; sichere Voreinstellungen; keine Secrets und keine personenbezogenen Daten in Ausgaben; nutzbar aus Cron und interaktiv; testbar ohne laufenden Stack.

**Non-Goals:** siehe Proposal.

## Decisions

### 1. Ein Einstiegspunkt, gemeinsame Bibliothek

`scripts/ops/nakctl <bereich> <befehl> [optionen]` dispatcht auf Funktionen in `scripts/ops/lib.sh`. `lib.sh` übernimmt: Wechsel ins Repo-Verzeichnis (oder `NAK_DEPLOY_DIR`), Lesen einzelner Schlüssel aus `.env` per `grep` ohne `source` (keine Ausführung von `.env`-Inhalt), `docker compose`-Aufrufe mit dem konfigurierten `COMPOSE_FILE`, Bestätigungsabfrage, `--dry-run`, `--yes`, farbige Ausgabe nur auf einem TTY.

*Alternative:* ein Python-CLI im Backend-Image (`python -m app.ops`). Verworfen, weil Backup und Log-Analyse auf dem Host laufen müssen und das Werkzeug auch bei nicht startendem Backend funktionieren soll. Die bestehenden Skripte bleiben unverändert und werden nur aufgerufen.

### 2. Valkey-Zugriff

Alle Valkey-Befehle laufen per `docker compose exec -T valkey sh -c 'REDISCLI_AUTH="$VALKEY_PASSWORD" valkey-cli …'`, damit das Passwort weder auf der Host-Kommandozeile noch in `ps` erscheint.

- `queue status`: `LLEN celery`, `HLEN unacked`, Anzahl `celery-task-meta-*` per `SCAN` (kein `KEYS`), Zahl aktiver Worker per `celery inspect ping` im `worker`-Container.
- `queue inspect [--limit N]`: liest höchstens N Nachrichten per `LRANGE`, dekodiert im Skript nur den Header `task` und zählt je Task-Name. Argumente und `kwargs` werden nie ausgegeben.
- `queue purge`: zeigt zuerst das Histogramm, warnt bei Mail-Tasks (`event_mail_hook_*`, Erinnerungen) ausdrücklich, verlangt die Eingabe des Wortes `LEEREN` oder `--yes`, und führt dann `celery -A app.celery_app purge -f` im `worker`-Container aus. `unacked` wird nur mit `--include-unacked` und nur bei gestoppten Workern geleert; sonst bricht der Befehl ab. Empfehlung im Hilfetext: vorher `beat` stoppen.
- `queue purge-results`: `SCAN MATCH celery-task-meta-*` plus `UNLINK` in Blöcken.
- `FLUSHALL`/`FLUSHDB` werden nie verwendet, damit Rate-Limit-Zähler und andere Schlüssel erhalten bleiben.
- Jeder ändernde Queue-Befehl schreibt eine Zeile (Zeit, Befehl, Anzahl, Betriebssystem-Benutzer) nach `logs/nakctl.log` im Deploy-Verzeichnis.

### 3. Backup

`backup create|verify|restore` rufen `scripts/backup.sh` bzw. `scripts/restore.sh` mit denselben Variablen auf; `--keycloak` setzt `DB_CONTAINER`, `POSTGRES_USER` und `POSTGRES_DB` für `keycloak-db`, wie in `production-compose.md` beschrieben. `backup list` zeigt je Zeitstempel Datenbankarchiv, Rollenarchiv, Größe und Alter und markiert unvollständige Paare. `status` und `backup list --max-age-hours H` liefern Exit-Code 1, wenn das jüngste vollständige Backup älter als H Stunden ist (Standard 26), damit Cron oder Monitoring alarmieren können.

### 4. Log-Analyse

`logs analyze` holt `docker compose logs --no-color --since <dauer> [dienste]` und gibt den Strom an `scripts/ops/analyze_logs.py` (stdin, nur Standardbibliothek). Das Python-Skript

- ordnet Zeilen dem Compose-Dienst zu und parst Level und Logger, sofern das Backend-Format vorliegt;
- zählt ERROR/WARNING/CRITICAL je Dienst und die häufigsten normalisierten Meldungen (Zahlen, UUIDs und Zeitstempel durch Platzhalter ersetzt);
- erkennt HTTP-5xx aus Uvicorn-Access-Logs, `Task … raised`, `Retry in`, `Hard time limit`, Rate-Limiter-Fallback und Audit-Schreibfehler über eine benannte Musterliste;
- redigiert vor jeder Ausgabe: Pfade `/export/<token>/` und `/calendar/<token>`, `Bearer …`, `password=`, `token=`, `secret=`, E-Mail-Adressen;
- gibt Text oder mit `--json` maschinenlesbar aus; Exit-Code 1, wenn `--fail-on-errors` gesetzt ist und Fehler gefunden wurden.

`logs export --since … [--service …] --output <datei>` schreibt die redigierten Rohzeilen in eine Datei mit Rechten 0600.

*Alternative:* Analyse in Bash mit `grep`/`awk`. Verworfen, weil Redaktion und Normalisierung in Python sauber testbar sind.

### 5. Status

`status` kombiniert `docker compose ps --format json`, `curl` auf `/health` im `backend`-Container, `alembic current` gegen `alembic heads` im Backend-Image (nur lesend, Laufzeit-Credentials), `docker system df -v` für die Volumes und das Backup-Alter. Er ändert nichts und ist für Cron geeignet.

### 6. Exit-Codes

0 = ok, 1 = Befund (Warnung/Schwelle überschritten), 2 = Bedienfehler, 3 = Umgebung nicht nutzbar (Container fehlt, Docker nicht erreichbar), 4 = vom Benutzer abgebrochen.

## Risks / Trade-offs

- **Purge verwirft Arbeit unwiderruflich** → Histogramm vorab, ausdrückliche Bestätigung, Mail-Warnung, Protokollzeile; die fachlichen Jobs (Sync, Entwürfe, Lückenscan) laufen über Beat ohnehin erneut.
- **Celery-Interna (Schlüsselnamen) können sich mit Kombu-Versionen ändern** → Schlüsselnamen zentral in `lib.sh`, ein Integrationstest gegen einen Valkey-Container in CI prüft `queue status` und `queue purge`.
- **Log-Muster veralten** → Musterliste in `analyze_logs.py` mit Unit-Tests auf echten Beispielzeilen; unbekannte Fehler erscheinen trotzdem in der Fehlerzählung.
- **Redaktion übersieht ein Format** → Tests mit Negativbeispielen; `logs export` weist im Kopf darauf hin, den Auszug vor dem Teilen zu prüfen.

## Migration Plan

Rein additiv. Betreiber ziehen den neuen Release-Checkout; bestehende Aufrufe von `backup.sh`/`restore.sh` und Cron-Jobs funktionieren unverändert. Rollback: Verzeichnis `scripts/ops/` ignorieren.

## Open Questions

- Soll `nakctl` zusätzlich als `make`-Ziele (`make ops-status` …) erreichbar sein?
- Soll `backup create` optional eine Off-Site-Kopie anstoßen (Hook-Skript `BACKUP_POST_HOOK`)?
