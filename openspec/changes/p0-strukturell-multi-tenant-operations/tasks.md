## 1. TenantContext und TenantAwareRepository

> **Architekturentscheidung (2026-10-02):** Mandantentrennung wird in der Datenbank
> durchgesetzt (PostgreSQL RLS mit verifiziertem Tenant-Kontext), nicht durch ein
> `TenantAwareRepository`-Mixin. Begründung und Zuordnung in `design.md`, Decision 1 und 2
> (überarbeitet). Die Tasks unten sind damit **anders gelöst**; die Spalte „Umsetzung“
> nennt die Stelle im Code und den Test, der das Ziel belegt.

- [x] ~1.1 `TenantContext`-Klasse in `app/adapters/db/tenant_context.py`~ *(anders gelöst: `app/tenant.py` hält Subject und Rollen request-lokal; die effektiven Bezirke/Gemeinden ermittelt die RLS-Policy aus `memberships`, statt sie in der Anwendung zu cachen)*
- [x] ~1.2 FastAPI-Dependency `get_tenant_context()`~ *(anders gelöst: `TenantMiddleware` übernimmt nur das verifizierte Token-Subject; `_set_tenant_gucs` in `app/adapters/db/session.py` setzt `app.current_user_sub` bzw. `app.is_system_worker` pro Transaktion)*
- [x] ~1.3 `TenantAwareRepository`-Mixin mit Superadmin-Bypass und `bypass_tenant_filter()`~ *(anders gelöst: RLS-Policies (Migrationen `0014`, `0022` und die RLS-Abschnitte späterer Migrationen) filtern **jede** Abfrage, auch Raw-SQL und Bulk-Statements, die ein Mixin nicht erreicht. Superadmin- und System-Worker-Zugriff sind Teil der Policy; die Anwendungsrolle `nak_app` ist `NOBYPASSRLS`)*
- [x] ~1.4 Mixin auf alle mandantenfähigen Repositories anwenden~ *(anders gelöst: `test_every_tenant_table_has_rls_enabled` schlägt fehl, sobald eine Tabelle mit Tenant-Spalte ohne RLS existiert; neue Tabellen können also nicht vergessen werden)*
- [x] ~1.5 Manuelle `district_id`-Filter in Routern/Services entfernen~ *(entfällt: die verbleibenden Prüfungen sind Autorisierung (`require_role_in_district`, 403 statt leerer Ergebnisse) und laut `CLAUDE.md` Pflicht. Sie sind die erste von drei Schichten (Middleware/RBAC, `TenantValidationService`, RLS), keine Duplikate)*
- [x] ~1.6 Unit-Tests TenantContext aus Memberships~ *(anders gelöst: `tests/unit/test_tenant_context.py`, `test_tenant_middleware.py`, `test_tenant_validation.py`, `test_cross_tenant_isolation.py`)*
- [x] ~1.7 Integrationstests TenantAwareRepository~ *(anders gelöst: `tests/integration/test_rls_postgres.py` (Lesen, Schreiben, Verschieben in fremde Bezirke, Superadmin, System-Worker, gefälschtes Subject) und `test_tenant_isolation_api.py` (Ende-zu-Ende über die API); laufen in CI auf frisch migrierter Datenbank)*

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
- [x] 3.4 `alembic check` in CI aufgenommen — seit 2026-10-01 **blockierend**, nachdem die vorbestehende Drift bereinigt wurde (`docs/schema.md`, Abschnitt „Abgleich ORM ↔ Datenbank“). Ursprünglich **informativ, nicht blockierend** (`continue-on-error: true`). Ein blockierender Gate würde CI sofort für alle PRs rot machen: es besteht bereits substanzielle, vorbestehende Drift zwischen ORM-Modellen und migrierter DB (siehe `docs/schema.md`, Abschnitt "Bekannte Schema-Drift"). Eine dieser Ursachen (fehlender `notification.py`-Import in `orm_models/__init__.py`) wurde als Nebenfix behoben; der Rest bleibt bewusst offen für einen eigenen Reconciliation-Follow-up.

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
