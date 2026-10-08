## Context

Der NAK District Planner hat 24 Migrationen, aber keine CI-Prüfung, dass `alembic upgrade head` sauber läuft. Die Mandantentrennung erfolgt über manuelle `district_id`-Filter in den einzelnen Router-Implementierungen – ein fehleranfälliger Ansatz. Backup wird in der README erwähnt, aber es gibt kein automatisiertes Skript und keinen nachgewiesenen Restore.

Die bestehende Architektur (Hexagonal mit Ports/Adaptern) erlaubt eine zentrale Enforcement-Schicht auf Repository-Ebene ohne Änderung der Domain-Logik.

## Goals / Non-Goals

**Goals:**
- Jede Repository-Query für mandantenfähige Entitäten filtert automatisch nach `district_id` aus dem Request-Kontext.
- PostgreSQL-Exclusion Constraints verhindern zeitlich überlappende Events in derselben Gemeinde.
- CI schlägt fehl, wenn `alembic upgrade head` nicht gegen eine frische Datenbank läuft.
- Backup-Skript erstellt verschlüsselte Dumps; Restore-Skript stellt auf separater Umgebung wieder her.
- RPO ≤ 24h, RTO ≤ 4h sind definiert.

**Non-Goals:**
- Kein vollständiges Multi-Region-Deployment.
- Kein Point-in-Time-Recovery (zunächst vollständige Dumps).
- Keine Ablösung von PostgreSQL RLS (Row Level Security) – wir nutzen Application-Layer Enforcement.
- Kein Kubernetes/Container-Orchestrierung-Backup (Volume Snapshots).

## Decisions

### Decision 1 (überarbeitet 2026-10-02): Tenant-Kontext aus dem verifizierten Token, Auswertung in der Datenbank

**Ursprünglich geplant:** ein request-scoped `TenantContext` mit vorberechneten
`effective_district_ids`, injiziert per FastAPI-Dependency. PostgreSQL RLS war nur als
„Option für zukünftige Härtung“ genannt.

**Umgesetzt:** Die Anwendung reicht nur das **verifizierte** Token-Subject weiter
(`TenantMiddleware` → `app/tenant.py`). Pro Transaktion setzt `_set_tenant_gucs`
(`app/adapters/db/session.py`) die GUCs `app.current_user_sub` bzw.
`app.is_system_worker`. Welche Bezirke und Gemeinden sichtbar sind, wertet die RLS-Policy
direkt aus `memberships` aus.

**Rationale:**
- Es gibt keine zweite, vorberechnete Kopie der Berechtigungen, die veralten kann.
  Eine entzogene Membership wirkt ab der nächsten Abfrage.
- Ein nicht verifiziertes Subject erreicht die Datenbank nicht. Ein gefälschtes Subject
  ohne Benutzer sieht nichts (`test_forged_subject_without_user_row_sees_nothing`).

### Decision 2 (überarbeitet 2026-10-02): RLS statt `TenantAwareRepository`-Mixin

**Ursprünglich geplant:** ein Mixin, das `list/get/update/delete` der Repositories auf
`effective_district_ids` filtert, mit Superadmin-Ausnahme und `bypass_tenant_filter()`.

**Umgesetzt:** Row-Level Security auf allen Tabellen mit Tenant-Spalte, ausgeführt als
Anwendungsrolle `nak_app` (`NOBYPASSRLS`). Superadmin und System-Worker sind Teil der
Policy statt eines Bypass-Schalters im Code.

**Rationale gegenüber dem Mixin:**
- RLS greift für **jede** Abfrage: Raw-SQL (`text()`), Bulk-UPDATE/DELETE, Joins über
  Hilfstabellen und neue Repositories. Ein Mixin schützt nur Methoden, die es kennt.
- Vollständigkeit ist testbar: `test_every_tenant_table_has_rls_enabled` lässt CI
  fehlschlagen, wenn eine neue Tabelle mit Tenant-Spalte ohne RLS entsteht.
- Kein Bypass-Pfad im Anwendungscode, der versehentlich offen bleiben kann.

**Kosten:** Bindung an PostgreSQL (ohnehin gesetzt) und Policy-Overhead. Gemessen in
`tests/performance/test_rls_overhead.py` und dokumentiert in
`docs/security/tenant-isolation.md`.

**Verhältnis zu Router-Prüfungen:** Die Prüfungen mit `require_role_in_district` und
`TenantValidationService` bleiben. Sie liefern 403 statt stiller leerer Ergebnisse und
sind die vorgelagerte Schicht. RLS ist die letzte Schicht, falls eine davon fehlt
(Defense in Depth, `docs/security/tenant-isolation.md`).

### Decision 3: Exclusion Constraints als letzte Absicherung

**Entscheidung:** PostgreSQL Exclusion Constraints auf `events`-Tabelle für `(congregation_id, daterange(start, end, '[]')) WITH &&`.

```sql
ALTER TABLE events ADD CONSTRAINT no_overlapping_events
EXCLUDE USING GIST (
    congregation_id WITH =,
    daterange(start_date, end_date, '[]') WITH &&
);
```

**Alternative:** Application-Layer-Prüfung in Service.
**Rationale:** Exclusion Constraints sind die einzige Garantie gegen Race-Conditions. Application-Layer-Prüfung bleibt als UX-Schicht davor.

### Decision 4: CI-Migration-Check als separater Workflow-Job

**Entscheidung:** Der CI-Job startet eine PostgreSQL-Datenbank (wie bestehende Integrationstests), führt `alembic upgrade head` aus, prüft Exit-Code, führt `alembic downgrade -1` aus, prüft Exit-Code, dann `alembic upgrade head` erneut.

**Erweiterung:** Optional Seed-Daten einspielen und per `alembic check` prüfen, ob das Schema mit den ORM-Modellen übereinstimmt.

### Decision 5: Backup/Restore als Shell-Skripte mit env-Konfiguration

**Entscheidung:**
- `scripts/backup.sh` nutzt `pg_dump -Fc` (custom format, komprimiert), verschlüsselt mit `gpg`, speichert in konfigurierbarem Verzeichnis.
- `scripts/restore.sh` nutzt `pg_restore`, prüft Datenbankexistenz, fragt vor Überschreiben.
- Konfiguration über Umgebungsvariablen (`BACKUP_DIR`, `BACKUP_ENCRYPT_KEY`, `DB_URL`).

**Kein** Kubernetes CronJob – die Skripte können per Docker-Container, Cron oder manuell ausgeführt werden.

## Risks / Trade-offs

- [RLS kann legitime Cross-Tenant-Operationen blockieren] → Superadmin und System-Worker (`app.is_system_worker`, nur im Celery-Worker gesetzt) sind Teil der Policy; abgedeckt durch `test_superadmin_bypass_sees_all_districts` und `test_system_worker_sees_all_districts`.
- [Exclusion Constraints erschweren Datenmigration] → Migrationen müssen temporär Constraints deaktivieren können.
- [Backup-Skript bei fehlender GPG-Key-Konfiguration nutzlos] → Production-Guard prüft Backup-Key bei Start in Production.
- [CI-Migration-Check verlängert CI-Laufzeit] → ~30s zusätzlich, akzeptabel.

## Migration Plan

1. ~~`TenantContext`-Klasse + FastAPI-Dependency~~ → verifizierter Tenant-Kontext + GUCs (Decision 1, überarbeitet).
2. ~~`TenantAwareRepository`-Mixin~~ → RLS auf allen Tenant-Tabellen (Decision 2, überarbeitet).
3. ~~Manuelle `district_id`-Filter entfernen~~ → entfällt; Router-Prüfungen bleiben als Autorisierungsschicht.
4. Cross-Tenant-Tests gegen echte RLS (`test_rls_postgres.py`, `test_tenant_isolation_api.py`).
5. Migration für Exclusion Constraints erstellen und testen.
6. CI-Migration-Check-Job in `.github/workflows/ci.yml` ergänzen.
7. Backup/Restore-Skripte erstellen, im Runbook dokumentieren.
8. Restore-Test auf separater Umgebung durchführen und protokollieren.

Rollback: RLS-Policies sind per Migration-Downgrade entfernbar (nicht per Feature-Flag, bewusst: ein Schalter wäre ein Bypass). Exclusion Constraints per `DROP INDEX IF EXISTS` rückgängig machbar.
