## Why

Die Produktreife-Analyse identifiziert drei strukturelle P0-Lücken, die mehr als oberflächliche Guards erfordern:

1. **Mandantentrennung ist nicht systematisch erzwingen:** Aktuell wird `district_id` in jedem Query manuell gesetzt. Ein Fehler in einer einzelnen Query kann Daten aus anderen Bezirken preisgeben. Es fehlt ein zentraler Enforcement-Mechanismus.
2. **CI-Prüfung von Migrationen fehlt:** `alembic upgrade head` wird in CI nicht gegen eine frische PostgreSQL-Datenbank getestet. Defekte Migrationen können erst beim Deployment auffallen.
3. **Backup/Restore ist nicht nachweisbar:** Es gibt kein automatisiertes Backup-Skript und keinen dokumentierten, getesteten Restore-Prozess. Ohne Restore-Test ist das Backup wertlos.

Diese Lücken betreffen nicht nur die Sicherheit, sondern die grundsätzliche Betriebsfähigkeit des Systems.

## What Changes

- **Multi-Tenant-Enforcement-Layer:** Ein zentraler `tenant_context` (Request-scoped) mit automatischer `district_id`-Filterung in allen Repository-Queries. Ein Mixin/Base-Klasse für alle mandantenfähigen Repositories erzwingt die Filterung.
- **DB-Level Exclusion Constraints:** PostgreSQL-Exclusion-Constraints für Zeitüberschneidungen bei Events und PlanningSlots (gleiche congregation_id + überlappender Zeitraum).
- **CI-Migration-Check:** Neuer CI-Job, der `alembic upgrade head` gegen eine frische PostgreSQL-Datenbank testet, Seed-Daten einspielt und `alembic downgrade -1` prüft.
- **Backup/Restore-Automatisierung:** Backup-Skript (`pg_dump` + Verschlüsselung), Restore-Skript (`pg_restore` + Integritätsprüfung), Runbook-Erweiterung mit RPO/RTO-Definition.

## Capabilities

### New Capabilities
- `tenant-enforcement-layer`: Automatische, zentrale Mandantentrennung auf Repository-Ebene.
- `data-integrity-constraints`: DB-Exclusion-Constraints für Zeitkonflikte.
- `migration-ci-validation`: CI-Job, der Migrationen gegen frische DB testet.
- `backup-restore-automation`: Skriptgestützte Backup- und Restore-Prozesse.

### Modified Capabilities
- Betriebsdokumentation: Runbook mit RPO/RTO, Restore-Protokoll, Backup-Rotation.
- CI-Pipeline: Neuer Migration-Check-Job.

## Impact

- Backend: Base-Repository-Refactoring, neue Migrationen (Exclusion Constraints).
- Betrieb: Neue Skripte `scripts/backup.sh` und `scripts/restore.sh`.
- CI: Neuer GitHub Actions Job (`migration-check.yml` oder erweiterter `ci.yml`).
- Dokumentation: Erweitertes Runbook mit RPO/RTO.
- Datenbank: Exclusion Constraints erfordern PostgreSQL-spezifische Indizes.
