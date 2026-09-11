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
| IDP-Provisioning (falls aktiv) | `IDP_PROVISIONING_API_KEY` und `IDP_PROVISIONING_ENDPOINT` (HTTPS) gesetzt |
| `SUPERADMIN_SUB` (optional) | Wenn gesetzt, wird dieser User erzwungen; sonst wird der erste User automatisch Superadmin |
| Backup-Key | `BACKUP_ENCRYPT_KEY` ist gesetzt fuer verschluesselte Backups |

Der Production Guard verhindert den Start, wenn kritische Werte nicht gesetzt sind.

## 2. Standard-Deployment

1. Aktuellen Code bereitstellen (`main`/Release-Tag)
2. Images bauen: `docker compose -f docker-compose.yml build`
3. Migrationen ausfuehren: `docker compose -f docker-compose.yml run --no-deps --rm backend alembic upgrade head`
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

**Ohne dokumentierten Restore-Test in einer separaten Umgebung gilt die Backup-Strategie
als unvollständig** — ein Restore-Test ist mindestens vierteljährlich durchzuführen und
hier zu protokollieren:

| Datum | Umgebung | Ergebnis | Durchgeführt von |
|-------|----------|----------|-------------------|
| _(noch kein Eintrag)_ | | | |

### 4.3 Verantwortlichkeit

Backup/Restore-Verantwortung liegt beim Backend-Team (siehe `openspec/security-roadmap.md`,
Abschnitt Verantwortlichkeiten).

## 5. Monitoring und Alarmierung (Minimum)

- Container-Status und Restart-Raten beobachten.
- Fehlerlogs fuer Backend/Worker aktiv monitoren.
- OIDC/IDP Erreichbarkeit und Token-Fehlerquote ueberwachen.

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

Der Job `alembic-check` (`.github/workflows/alembic-check.yml`) muss als
**erforderlicher Status-Check** auf dem `main`-Branch konfiguriert sein
(GitHub → Settings → Branches → Branch protection rule für `main` →
"Require status checks to pass" → `alembic-check` auswählen). Ohne diesen
Zwang kann ein PR mit gebrochener Migration (mehrere Heads, kaputter
Downgrade-Pfad, Seed-Inkonsistenz) gemerged werden, auch wenn der Check rot
ist. Der informative Drift-Teilschritt (`alembic check`, siehe
`docs/schema.md`) ist bewusst **nicht** blockierend und muss nicht als
eigener Required Check gelistet werden — nur der Gesamtjob-Status zählt.

Diese Einstellung kann nicht aus dem Repository-Code heraus gesetzt werden
und muss von einem Repo-Admin manuell vorgenommen (oder per `gh api
repos/{owner}/{repo}/branches/main/protection` gesetzt) werden.
