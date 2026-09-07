## 1. TenantContext und TenantAwareRepository

- [ ] 1.1 `TenantContext`-Klasse in `app/adapters/db/tenant_context.py` definieren
  - `user_sub`, `effective_district_ids`, `effective_congregation_ids`, `is_superadmin`
- [ ] 1.2 FastAPI-Dependency `get_tenant_context()` in `app/adapters/api/deps.py` ergänzen
  - Ermittelt aus `CurrentUserWithMemberships` die effektiven district_ids/congregation_ids
- [ ] 1.3 `TenantAwareRepository`-Mixin in `app/adapters/db/base.py`
  - `_apply_tenant_filter(query)` für `list`, `get`, `update`, `delete`
  - Superadmin-Bypass
  - Explizite `bypass_tenant_filter()`-Contextmanager für Service-Accounts
- [ ] 1.4 Mixin auf alle mandantenfähigen Repositories anwenden:
  - `SqlEventRepository`
  - `SqlLeaderRepository`
  - `SqlServiceAssignmentRepository`
  - `SqlCalendarIntegrationRepository`
  - `SqlPlanningSlotRepository`
  - `SqlPlanningSeriesRepository`
  - `SqlExportTokenRepository`
  - `SqlInvitationRepository`
  - `SqlCongregationRepository`
  - `SqlDistrictRepository`
- [ ] 1.5 Bestehende manuelle `district_id`-Filter in Routern/Servern aufräumen (Duplikation entfernen)
- [ ] 1.6 Unit-Tests: TenantContext-Ermittlung aus Memberships
- [ ] 1.7 Integrationstests: TenantAwareRepository filtert korrekt

## 2. Exclusion Constraints

- [ ] 2.1 Migration erstellen: Exclusion Constraint `no_overlapping_events` auf `events`-Tabelle
  - `congregation_id WITH =, daterange(start_date, end_date, '[]') WITH &&`
  - GIST-Index erforderlich
- [ ] 2.2 Migration erstellen: Exclusion Constraint `no_overlapping_planning_slots` auf `planning_slots`
  - `congregation_id WITH =, daterange(planning_date, planning_date, '[]') WITH &&`
- [ ] 2.3 Migration testen: Einfügen überlappender Events → DB-Constraint-Verletzung
- [ ] 2.4 `alembic downgrade`-Test: Constraints werden sauber entfernt
- [ ] 2.5 Dokumentation: Constraints in `docs/schema.md` festhalten

## 3. CI-Migration-Check

- [x] 3.1 Migrations-Checks erweitert *(statt eines neuen Jobs in `ci.yml` — der bestehende `.github/workflows/alembic-check.yml` deckte Single-Head/FK-Namen/Offline-SQL/Apply bereits ab, um Redundanz zu vermeiden dort ergänzt statt dupliziert)*:
  - PostgreSQL-Service-Container: bereits vorhanden
  - `alembic upgrade head` → Exit-Code prüfen: bereits vorhanden
  - `alembic downgrade -1` → Exit-Code prüfen: **neu ergänzt**
  - `alembic upgrade head` → erneut (Roundtrip-Test): **neu ergänzt**
  - Seed-Daten via `make seed-dry-run`-Äquivalent (`seed_testdata.py --dry-run`) + Konsistenzprüfung: **neu ergänzt**
- [x] 3.2 Migration-Check als erforderlichen Check in Branch-Protection-Regeln dokumentiert (`docs/production-runbook.md` Abschnitt 7.1). Das tatsächliche Setzen der GitHub-Branch-Protection-Regel erfordert Repo-Admin-Zugriff und wurde **nicht** automatisch vorgenommen.
- [x] 3.3 Kritische Constraints dokumentiert (`docs/schema.md`: FK-Namenskonvention, Unique Constraints, Tenant-Scoping-FKs, bekannte Schema-Drift)
- [x] 3.4 `alembic check` in CI aufgenommen — **informativ, nicht blockierend** (`continue-on-error: true`). Ein blockierender Gate würde CI sofort für alle PRs rot machen: es besteht bereits substanzielle, vorbestehende Drift zwischen ORM-Modellen und migrierter DB (siehe `docs/schema.md`, Abschnitt "Bekannte Schema-Drift"). Eine dieser Ursachen (fehlender `notification.py`-Import in `orm_models/__init__.py`) wurde als Nebenfix behoben; der Rest bleibt bewusst offen für einen eigenen Reconciliation-Follow-up.

## 4. Backup/Restore-Automatisierung

- [ ] 4.1 `scripts/backup.sh` erstellen:
  - `pg_dump -Fc` (custom format, komprimiert)
  - GPG-Verschlüsselung mit konfigurierbarem Key
  - Timestamp-basierte Dateinamen
  - Konfiguration via `BACKUP_DIR`, `BACKUP_ENCRYPT_KEY`, `DATABASE_URL`
  - Maximale Aufbewahrung konfigurierbar (`BACKUP_RETENTION_DAYS`)
- [ ] 4.2 `scripts/restore.sh` erstellen:
  - `pg_restore` mit Bestätigung vor Überschreiben
  - Integritätsprüfung (`pg_restore --list` vorab)
  - Dry-Run-Modus
- [ ] 4.3 Production-Guard-Prüfung: `BACKUP_ENCRYPT_KEY` in Production gesetzt?
- [ ] 4.4 Runbook in `docs/production-runbook.md` erweitern:
  - RPO ≤ 24h, RTO ≤ 4h definieren
  - Backup-Erstellungs-Rhythmus (täglich)
  - Restore-Protokoll (Schritt-für-Schritt)
  - Aufbewahrungsfrist (30 Tage)
  - Verantwortlichkeit
- [ ] 4.5 Restore-Test auf separater Umgebung durchführen und protokollieren:
  - Backup erstellen
  - Auf Test-Umgebung einspielen
  - Anwendung starten
  - Datenintegrität prüfen
  - Datum + Ergebnis dokumentieren
- [ ] 4.6 Backup-Strategie in README.md aktualisieren
