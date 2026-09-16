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

> **Hinweis (2026-09-07):** Diese Spezifikation ist gegen ein Schema geschrieben, das es
> nicht mehr gibt — die `events`-Tabelle wurde im M3-Umbau durch `event_instances` +
> `planning_slots` ersetzt (siehe Migration `0125`). `event_instances` hat keine eigene
> `congregation_id`-Spalte (nur indirekt über `planning_slot_id`), und `planning_slots`
> hat `planning_date`/`planning_time` als Zeitpunkt statt als Zeitspanne — ein
> GIST-Exclusion-Constraint mit `daterange`/`&&` passt auf keine der beiden Tabellen mehr
> wie ursprünglich beschrieben. Nutzerentscheidung: einfachere, schema-korrekte Variante
> statt Schema-Redesign — siehe unten.

- [x] ~2.1 Exclusion Constraint `no_overlapping_events` auf `events`~ *(entfällt — Tabelle existiert nicht mehr, siehe Hinweis oben)*
- [x] 2.2 Migration erstellt: partieller Unique-Index `no_overlapping_planning_slots` auf
  `planning_slots (congregation_id, planning_date, planning_time)`, `WHERE congregation_id
  IS NOT NULL AND status = 'ACTIVE'` *(kein GIST/daterange-EXCLUDE — `planning_slots` hat
  keine Zeitspanne, sondern nur einen Zeitpunkt; ein exaktes Unique reicht für die
  gewünschte "keine Doppelbuchung zur exakt gleichen Zeit"-Regel. Echtes
  Zeitspannen-Overlap bleibt Aufgabe von `p1-domain-conflict-quality`, siehe `docs/schema.md`.)*
- [x] 2.3 Migration getestet: Duplikat (gleiche Gemeinde/Datum/Zeit, beide ACTIVE) → Constraint-Verletzung bestätigt; Cancelled-Duplikat, NULL-congregation-Duplikat und abweichende Zeit → erfolgreich (siehe `docs/schema.md`)
- [x] 2.4 `alembic downgrade`-Test: Index wird sauber entfernt und beim erneuten Upgrade wiederhergestellt (Roundtrip verifiziert)
- [x] 2.5 Dokumentation in `docs/schema.md` festgehalten (Abschnitt "Überlappungsschutz")

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

- [x] 4.1 `scripts/backup.sh` erstellen:
  - `pg_dump -Fc` (custom format, komprimiert) — läuft via `docker exec` im `db`-Container,
    kein `pg_dump`-Client auf dem Host nötig
  - GPG-Verschlüsselung mit konfigurierbarem Key
  - Timestamp-basierte Dateinamen
  - Konfiguration via `BACKUP_DIR`, `BACKUP_ENCRYPT_KEY`, `DB_CONTAINER` *(statt `DATABASE_URL` —
    das Skript verbindet sich nicht direkt zur DB, sondern nutzt den laufenden Container, da der
    DB-Port in Produktion nicht nach außen exponiert ist)*
  - Maximale Aufbewahrung konfigurierbar (`BACKUP_RETENTION_DAYS`)
- [x] 4.2 `scripts/restore.sh` erstellen:
  - `pg_restore` mit Bestätigung vor Überschreiben (`--yes` zum Überspringen)
  - Integritätsprüfung (`pg_restore --list` vorab, bricht bei korruptem Archiv ohne Änderung ab)
  - Dry-Run-Modus (`--dry-run`)
- [x] 4.3 Production-Guard-Prüfung: `BACKUP_ENCRYPT_KEY` in Production gesetzt? *(`app/config.py::production_guard`, Tests in `tests/unit/test_production_guard.py`)*
- [x] 4.4 Runbook in `docs/production-runbook.md` erweitert:
  - RPO ≤ 24h, RTO ≤ 4h definiert
  - Backup-Erstellungs-Rhythmus (täglich)
  - Restore-Protokoll (Schritt-für-Schritt)
  - Aufbewahrungsfrist (30 Tage)
  - Verantwortlichkeit
- [ ] 4.5 Restore-Test auf separater Umgebung durchführen und protokollieren *(bewusst offen gelassen — erfordert eine echte Staging-Infrastruktur, die hier nicht verfügbar ist; die Skript-Logik selbst wurde per End-to-End-Test gegen einen Wegwerf-Container verifiziert: Backup → Datenänderung → Restore → Originaldaten wiederhergestellt, inkl. Fehlerfall "korruptes Archiv" und Klartext-Warnung ohne `BACKUP_ENCRYPT_KEY`. Protokoll-Tabelle für den echten Test steht bereit in `docs/production-runbook.md` Abschnitt 4.2.)*
- [x] 4.6 Backup-Strategie in README.md aktualisiert
