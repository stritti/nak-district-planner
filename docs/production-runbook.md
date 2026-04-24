# Production Runbook

Dieses Runbook beschreibt den operativen Mindestablauf fuer produktive Deployments.

## 1. Voraussetzungen

- Gueltige `.env` fuer Produktion (keine Dev-Secrets)
- Laufende Infrastruktur: Reverse Proxy, Datenbank, Redis
- Backup-Strategie fuer PostgreSQL vorhanden

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

- Backup via `pg_dump` regelmaessig erstellen.
- Restore-Prozess mindestens periodisch in Staging testen.
- Ohne Restore-Test gilt Backup-Strategie als unvollstaendig.

## 5. Monitoring und Alarmierung (Minimum)

- Container-Status und Restart-Raten beobachten.
- Fehlerlogs fuer Backend/Worker aktiv monitoren.
- OIDC/IDP Erreichbarkeit und Token-Fehlerquote ueberwachen.

## 6. Security Operations

- Regelmaessige Rotation kritischer Secrets.
- Security-Scans aus CI regelmaessig auswerten.
- Bei Incident: Zeitstrahl, Scope, Mitigation und Follow-up dokumentieren.

## 7. Release-Disziplin

- Commit- und Release-Prozess gemaess `docs/release-process.md`.
- Produktive Deployments bevorzugt aus versionierten Releases.
