# Production Runbook

Dieses Runbook beschreibt den operativen Mindestablauf fuer produktive Deployments.

## 1. Voraussetzungen

- Gueltige `.env` fuer Produktion (keine Dev-Secrets)
- Laufende Infrastruktur: Reverse Proxy, Datenbank, Redis
- Backup-Strategie fuer PostgreSQL vorhanden

### 1.1 Production-Config-Checkliste

Vor jedem Deployment in Produktion pruefen:

| Pruefung | Erwartung |
|----------|-----------|
| `APP_ENV=production` | Production Guard ist aktiv |
| `SECRET_KEY` | Min. 32 Zeichen, nicht `replace-with-*` |
| `OIDC_CLIENT_SECRET` | Echter Wert, nicht `replace-with-*` |
| `OIDC_DISCOVERY_URL` | Echte URL (HTTPS), nicht `oidc.example.com` |
| `OIDC_CLIENT_ID` | Echter Wert, nicht `replace-with-oidc-client-id` |
| Debug-Modus | `DEBUG` ist nicht `true` (oder gar nicht gesetzt) |
| CORS-Origins | Nicht `["*"]` |
| OIDC-Redirect-URIs | Verwenden HTTPS |
| `CONFLICT_CHECK_ENABLED` | Standardmäßig aktiv (`true`); nur bei Notfällen deaktivieren — die Konfliktprüfung verhindert Doppelbuchungen und Zuweisungen abwesender Amtsträger (siehe `docs/conflict-rules.md`) |
| IDP-Provisioning (falls aktiv) | `IDP_PROVISIONING_API_KEY` und `IDP_PROVISIONING_ENDPOINT` (HTTPS) gesetzt |
| `SUPERADMIN_SUB` (optional) | Wenn gesetzt, wird dieser User erzwungen; sonst wird der erste User automatisch Superadmin |
| Backup-Key | `BACKUP_ENCRYPT_KEY` ist gesetzt fuer verschluesselte Backups |
| `CALENDAR_ALLOW_INSECURE_URLS` | `false` (in Produktion erzwungen; Start von API, Worker und Beat schlaegt sonst fehl) |
| `CALENDAR_NAT64_PREFIXES` | Nur bei IPv6-only-Hosts mit DNS64/NAT64 und netzspezifischem Praefix (RFC 6052) setzen: kommagetrennte IPv6-CIDRs der Laenge 32/40/48/56/64/96, z. B. `2001:db8:64::/96`. Ohne Eintrag koennten Kalender-URLs ueber das NAT64-Praefix interne IPv4-Ziele erreichen (SSRF). `64:ff9b::/96` und `64:ff9b:1::/48` werden immer geprueft. Ungueltige Werte verhindern den Start. |

Der Production Guard verhindert den Start, wenn kritische Werte nicht gesetzt sind.

## 2. Standard-Deployment

1. Aktuellen Code bereitstellen (`main`/Release-Tag)
2. Images bauen: `docker compose -f docker-compose.yml build`
3. Migrationen ausfuehren: `docker compose -f docker-compose.yml run --no-deps --rm --build migrate alembic upgrade head`
4. Stack starten/aktualisieren: `docker compose -f docker-compose.yml up -d`
5. Health pruefen: `curl http://localhost/api/health`

## 3. Rollback (Basisverfahren)

1. Vor Deployment DB-Backup erstellen.
2. Bei Fehlern auf letztes stabiles Release zurueckgehen.
3. Wenn noetig DB-Restore aus validiertem Backup.
4. Post-Rollback Smoke-Test (Login, Eventliste, Matrix, Export).

## 4. Backup und Restore

**Ziele:** RPO ≤ 24h (max. 1 Tag Datenverlust), RTO ≤ 4h (max. 4h bis Wiederherstellung).

### 4.1 Backup erstellen

```bash
BACKUP_ENCRYPT_KEY=<gpg-recipient> ./scripts/backup.sh
```

- Läuft täglich (Cron oder externer Scheduler — kein Kubernetes-CronJob in diesem Setup).
- Nutzt `pg_dump -Fc` innerhalb des `db`-Containers, verschlüsselt das Ergebnis mit GPG
  (`BACKUP_ENCRYPT_KEY`), bevor es den Container verlässt.
- `production_guard()` verweigert den Start in Produktion, wenn `BACKUP_ENCRYPT_KEY` fehlt.
- Aufbewahrung: 30 Tage Standard (`BACKUP_RETENTION_DAYS`), ältere Backups werden automatisch gelöscht.
- Ablagepfad (`BACKUP_DIR`) muss selbst regelmäßig extern gesichert werden (Backup-Rotation).

### 4.2 Restore durchführen

```bash
./scripts/restore.sh <backup-datei>.dump.gpg --dry-run   # Integritätsprüfung ohne Änderung
./scripts/restore.sh <backup-datei>.dump.gpg              # mit Bestätigungsabfrage
```

Schritt-für-Schritt:
1. Backup-Datei bereitstellen (entschlüsselt automatisch, wenn `.gpg`).
2. `--dry-run` ausführen — prüft Archiv-Integrität via `pg_restore --list`, ändert nichts.
3. Ohne `--dry-run` ausführen — fragt vor dem Überschreiben explizit nach Bestätigung.
4. Nach dem Restore: Anwendung neu starten, Health-Check + Smoke-Test (siehe Abschnitt 3) durchführen.
5. Ergebnis (Datum, Dauer, Auffälligkeiten) im Incident-/Ops-Log dokumentieren.

#### Automatisierter Restore-Drill

`scripts/restore-drill.sh` prüft die technische Wiederherstellbarkeit mit der gleichen
PostgreSQL-Major-Version wie die Produktionsumgebung. Der Drill verwendet zwei voneinander
getrennte PostgreSQL-18-Container:

1. Source-Datenbank mit Prüfdaten anlegen.
2. Mit dem produktiven `scripts/backup.sh` ein GPG-verschlüsseltes Backup erzeugen.
3. Source-Datenbank vollständig stoppen.
4. Unabhängige Target-Datenbank mit abweichenden Prüfdaten starten.
5. Das Backup mit dem produktiven `scripts/restore.sh` zuerst im `--dry-run` prüfen und
   anschließend wirklich wiederherstellen.
6. Wiederhergestellte Daten gegen die Source-Prüfdaten verifizieren.
7. Ein absichtlich beschädigtes Archiv prüfen; es muss vor einer Datenänderung abgewiesen
   werden und die Target-Daten müssen unverändert bleiben.

Der Workflow `.github/workflows/restore-drill.yml` führt diesen Drill für jeden Pull Request
gegen `main`, bei jedem Push auf `main`, wöchentlich sowie manuell aus. Der erfolgreiche
GitHub-Actions-Lauf `37014902252` vom 2. Oktober 2026 dokumentiert den ersten vollständigen
CI-Nachweis.

Der automatisierte Drill ersetzt nicht den vierteljährlichen Restore aus einem echten
Produktionsbackup in einer produktionsnahen Staging-Umgebung. Dieser Test prüft zusätzlich
externe Backup-Ablage, Berechtigungen, Betriebszugriffe und den realen Smoke-Test.

| Datum | Umgebung | Ergebnis | Durchgeführt von |
|-------|----------|----------|-------------------|
| 2026-10-02 | GitHub Actions, getrennte PostgreSQL-18-Source/Target-Container | Erfolgreich: GPG-Backup, Dry-Run, Restore, Datenvergleich und Korruptions-Negativtest | CI `Restore Drill` |
| _(vierteljährlicher Staging-Test ausstehend)_ | | | |

### 4.3 Verantwortlichkeit

Backup/Restore-Verantwortung liegt beim Backend-Team (siehe `openspec/security-roadmap.md`,
Abschnitt Verantwortlichkeiten).

## 5. Monitoring und Alarmierung (Minimum)

- Container-Status und Restart-Raten beobachten.
- Fehlerlogs fuer Backend/Worker aktiv monitoren.
- OIDC/IDP Erreichbarkeit und Token-Fehlerquote ueberwachen.
- Rate-Limiter-Fail-Open-Metrik `rate_limiter.fail_open` ueberwachen.

### 5.1 Rate-Limiter-Fail-Open

Der Counter wird erhöht, wenn Redis bei einer Rate-Limit-Prüfung nicht erreichbar
ist oder einen Fehler liefert. Das System lässt den Request in diesem Fall bewusst
zu, damit ein Redis-Ausfall nicht den gesamten Dienst blockiert.

- **Voraussetzung:** `OTEL_ENABLED=true` setzen und `OTEL_ENDPOINT` auf einen
  erreichbaren OTLP-Collector mit Metrics-Export konfigurieren. Die Metriken des
  Backends im Monitoring-Backend verfügbar machen und den Alert dort einrichten.
- **Alarm:** auslösen, sobald innerhalb von 5 Minuten mindestens ein Fail-Open-
  Ereignis auftritt; bei wiederholten Ereignissen als Incident behandeln.
- **Prüfung:** Das `reason`-Attribut der Metrik im Monitoring-Backend prüfen und
  mit dem Backend-Log korrelieren. Anschließend Redis-Erreichbarkeit, DNS,
  Credentials sowie Verbindungsgrenzen prüfen.
- **Recovery:** Redis wiederherstellen, anschließend einen kontrollierten Request
  ausführen und bestätigen, dass keine weiteren Fail-Open-Ereignisse auftreten.
- **Nachbereitung:** Ereignisdauer, Ursache und Gegenmaßnahme im Betriebstagebuch
  dokumentieren.

## 6. Security Operations

### 6.1 Secret-Lifecycle

Kritische Secrets (SECRET_KEY, OIDC_CLIENT_SECRET, IDP_PROVISIONING_API_KEY) unterliegen einem festgelegten Lifecycle:

**Erzeugung:**
- SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"` (64 Zeichen Hex)
- OIDC_CLIENT_SECRET: Wird durch den OIDC-Provider generiert (z. B. Keycloak Client Secret)
- IDP_PROVISIONING_API_KEY: Wird durch den IDP-Provisioning-Dienst (z. B. Webhook-Endpoint) generiert
- Alle Secrets werden im Secrets-Manager (z. B. Docker Secrets, HashiCorp Vault, 1Password Connect) gespeichert, **nicht** in der `.env`-Datei im Repository

**Rotationsintervall (Empfehlung):**

| Secret | Intervall | Begründung |
|--------|-----------|------------|
| `SECRET_KEY` | Alle 90 Tage oder bei Rotation eines anderen Secrets | Führt zur Ungültigkeit aller Sessions (User müssen neu einloggen) |
| `OIDC_CLIENT_SECRET` | Alle 90 Tage | Gängige OIDC-Praxis; kein Session-Verlust |
| `IDP_PROVISIONING_API_KEY` | Alle 90 Tage | Bei Kompromittierung: sofort rotieren |

**Rotationsverfahren:**
1. Neues Secret generieren und im Secrets-Manager hinterlegen
2. Deployment mit neuem Secret durchführen (Dienst neu starten)
3. Altes Secret im Secrets-Manager aufbewahren (Fallback für 48 h)
4. Nach erfolgreichem Monitoring (48 h) altes Secret endgültig löschen
5. Rotation im Betriebstagebuch dokumentieren

**Recovery:**
1. Wenn der aktuelle SECRET_KEY verloren geht: Backup wiederherstellen, das mit dem alten Key erstellt wurde
2. Neuen SECRET_KEY generieren (alle Sessions werden ungültig)
3. OIDC_CLIENT_SECRET beim OIDC-Provider zurücksetzen
4. Alle Benutzer über notwendigen Neulogin informieren

### 6.2 Security-Scans

- Regelmaessige Auswertung der CI-Scanner-Ergebnisse (Ruff, Bandit, Trivy).
- Schwachstellen-Monitoring fuer Python-Abhaengigkeiten via `pip-audit` oder Dependabot.
- Bei Incident: Zeitstrahl, Scope, Mitigation und Follow-up dokumentieren.

## 7. Release-Disziplin

- Commit- und Release-Prozess gemaess `docs/release-process.md`.
- Produktive Deployments bevorzugt aus versionierten Releases.

### 7.1 Erforderliche Branch-Protection-Checks

Für `main` muss das aktive GitHub-Ruleset Änderungen über Pull Requests erzwingen, aktuelle
Required Status Checks verlangen, Branch-Löschung und Non-Fast-Forward-Updates verhindern
und ohne regulären Bypass arbeiten. Für den v1-Release-Gate sind folgende stabilen
Check-Namen verbindlich:

- `Backend — Unit Tests & Coverage`
- `Frontend — Unit Tests`
- `Frontend — E2E Tests`
- `Migration Graph & FK Names`
- `Encrypted Backup & Isolated Restore`
- `MegaLinter`
- `Dependency Review`
- `CodeQL Analysis (python)`
- `CodeQL Analysis (javascript-typescript)`
- `Python Dependency Audit (pip-audit)`
- `Frontend Dependency Audit (bun audit)`
- `Build Backend Image`
- `Build Frontend Image`
- `Build documentation`

`Build documentation` läuft absichtlich auf jedem Pull Request gegen `main`, damit ein als
Required Check konfigurierter Status nicht wegen eines Workflow-Pfadfilters dauerhaft
`pending` bleibt. Die Docker-Build- und Frontend-Jobs dürfen bei nicht betroffenen Pfaden
intern als `skipped` enden, ihre stabilen Check-Namen werden aber durch die übergeordneten
PR-Workflows erzeugt.

`Backend — Unit Tests & Coverage` enthält das Coverage-Gate von mindestens 80 Prozent sowie
die unveränderte Integration-/Performance-Absicherung des CI-Workflows. Der Migrationsjob
enthält Single-Head-Prüfung, FK-Namen, Offline-SQL, Migration auf einer frischen
PostgreSQL-Datenbank, Downgrade/Upgrade-Roundtrip, Seed-Dry-Run und den blockierenden
`alembic check`. Der Restore-Job prüft die Wiederherstellbarkeit eines verschlüsselten
Backups in einer unabhängigen PostgreSQL-18-Zieldatenbank.

Das aktuell vorhandene Ruleset schützt bereits vor Branch-Löschung und
Non-Fast-Forward-Updates. Das Erzwingen von Pull Requests und Required Status Checks ist
Repo-Admin-Konfiguration und wird in GitHub-Issue #403 nachverfolgt. Der Repository-Code
allein kann diese Einstellung nicht erzwingen. Vor Veröffentlichung eines v1 Release
Candidate muss der tatsächliche Ruleset-Stand erneut gegen diese Liste verifiziert werden.
