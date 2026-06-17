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

### Decision 1: TenantContext als Request-scoped Dependency

**Entscheidung:** Ein `TenantContext`-Objekt wird pro Request aus dem authentifizierten User + dessen Memberships ermittelt und über FastAPI-Dependencies injiziert.

```python
class TenantContext:
    user_sub: str
    effective_district_ids: set[UUID]
    effective_congregation_ids: set[UUID]
    is_superadmin: bool
```

**Alternative:** PostgreSQL Row Level Security.
**Rationale:** Application-Layer Enforcement ist einfacher testbar und nicht an PostgreSQL gebunden. RLS bleibt als Option für zukünftige Härtung.

### Decision 2: BaseRepository mit automatischem Tenant-Filter

**Entscheidung:** Ein `TenantAwareRepository`-Mixin für SQLAlchemy-Repositories filtert alle `list()`, `get()`, `update()`, `delete()`-Operationen automatisch auf die `effective_district_ids` des TenantContext.

```python
class TenantAwareRepository:
    tenant_context: TenantContext
    
    def _apply_tenant_filter(self, query: Select) -> Select:
        if self.tenant_context.is_superadmin:
            return query  # No filter for superadmin
        return query.where(self.model.district_id.in_(
            self.tenant_context.effective_district_ids
        ))
```

**Alternative:** Manuelle Filter in jedem Router/Service.
**Rationale:** Automatische Filterung verhindert menschliche Fehler. Superadmin ist explizit ausgenommen.

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

- [TenantAwareRepository kann legitime Cross-Tenant-Operationen blockieren] → Superadmin-Ausnahme + explizite `bypass_tenant_filter()`-Methode für Service-Accounts.
- [Exclusion Constraints erschweren Datenmigration] → Migrationen müssen temporär Constraints deaktivieren können.
- [Backup-Skript bei fehlender GPG-Key-Konfiguration nutzlos] → Production-Guard prüft Backup-Key bei Start in Production.
- [CI-Migration-Check verlängert CI-Laufzeit] → ~30s zusätzlich, akzeptabel.

## Migration Plan

1. `TenantContext`-Klasse + FastAPI-Dependency implementieren.
2. `TenantAwareRepository`-Mixin implementieren, auf alle mandantenfähigen Repositories anwenden.
3. Bestehende manuelle `district_id`-Filter in Routern/Servern aufräumen (durch zentralen Filter ersetzt).
4. Cross-Tenant-Tests aus Package A erweitern, um automatischen Tenant-Filter zu prüfen.
5. Migration für Exclusion Constraints erstellen und testen.
6. CI-Migration-Check-Job in `.github/workflows/ci.yml` ergänzen.
7. Backup/Restore-Skripte erstellen, im Runbook dokumentieren.
8. Restore-Test auf separater Umgebung durchführen und protokollieren.

Rollback: TenantAwareRepository per Feature-Flag deaktivierbar. Exclusion Constraints per `DROP INDEX IF EXISTS` rückgängig machbar.
