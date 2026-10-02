# Datenbankschema: kritische Constraints

Dieses Dokument hält die Constraints fest, die bei jeder Migration bewusst
erhalten werden müssen — nicht das vollständige Schema (siehe
`services/backend/alembic/versions/` und `app/adapters/db/orm_models/` für
den vollständigen, aktuellen Stand).

## Foreign-Key-Namenskonvention

- Alle FK-Constraints folgen dem Muster `fk_<table>_<column>` (oder Variationen
  bei zusammengesetzten Keys).
- PostgreSQL kürzt Identifier über 63 Zeichen ohne Warnung — das führt zu
  Constraint-Namen, die nicht mehr zu den Migrationsdateien passen.
- Wird automatisch geprüft: `scripts/check_fk_names.py`, läuft in
  `.github/workflows/alembic-check.yml`.

## Kritische Unique Constraints

Diese drei Constraints sichern Kernannahmen der Anwendung ab — sie dürfen
nicht ohne explizite Migration und Team-Review entfernt werden:

| Constraint | Tabelle | Spalten | Zweck |
|------------|---------|---------|-------|
| `uq_users_sub` | `users` | `sub` | OIDC-Subject muss pro Nutzer eindeutig sein — Grundlage für Login/Identität. |
| `uq_memberships_user_role_scope` | `memberships` | `user_sub, role, scope_type, scope_id` | Verhindert doppelte Rollenzuweisungen für denselben Nutzer/Scope. |
| `event_instances_planning_slot_id_key` | `event_instances` | `planning_slot_id` | 1:1-Beziehung zwischen PlanningSlot und EventInstance (M1 Matrix-Rendering). |

## Überlappungsschutz: `no_overlapping_planning_slots`

Partieller Unique-Index auf `planning_slots (congregation_id, planning_date, planning_time)`
(Migration `0ea121ae36ad`), aktiv nur für `WHERE congregation_id IS NOT NULL AND status = 'ACTIVE'`:

- Verhindert zwei aktive Slots für dieselbe Gemeinde zur exakt gleichen Zeit (Doppelbuchung).
- Ausgenommen: `CANCELLED`-Slots (ein abgesagter und ein neuer Slot dürfen denselben
  Zeitpunkt belegen) und Slots mit `congregation_id IS NULL` (bezirksweite/Vorlagen-Slots,
  siehe `invitation_service.py`).
- **Kein echtes Zeitspannen-Overlap:** `planning_slots` hat nur `planning_time` (einen
  Zeitpunkt), keine Dauer. Ein 9:00-Uhr-Slot und ein 9:30-Uhr-Slot derselben Gemeinde
  gelten hier *nicht* als Konflikt, auch wenn der resultierende `event_instances`-Eintrag
  (mit `actual_start_at`/`actual_end_at`) sich zeitlich überschneiden würde. Echte
  Zeitspannen-Konfliktprüfung ist Aufgabe der App-Ebene
  (`openspec/changes/p1-domain-conflict-quality`), da `event_instances` keine eigene
  `congregation_id`-Spalte hat (nur indirekt über `planning_slot_id`) und ein
  PostgreSQL-EXCLUDE-Constraint nicht über einen Fremdschlüssel-Join hinweg funktioniert.
- Deckt sich mit der bestehenden App-Logik in `planning_series_generator.py`
  (`get_by_series_date`), die vor dem Erzeugen neuer Slots bereits auf Duplikate prüft —
  der DB-Constraint ist die letzte Verteidigungslinie, kein Ersatz dafür.
- Verletzung äußert sich aktuell als unbehandelter `IntegrityError` → HTTP 500 (kein
  bestehendes Error-Handling für Constraint-Verletzungen im Code gefunden, auch nicht für
  die älteren Unique Constraints oben). Eine nutzerfreundliche Fehlermeldung ist Teil von
  `p1-domain-conflict-quality`, nicht dieser Änderung.

## Tenant-Scoping (Fremdschlüssel)

Mandantenfähige Tabellen tragen `district_id` und/oder `congregation_id` als
Fremdschlüssel (siehe `docs/security/tenant-isolation.md` für die
RLS-Policies, die auf diesen Spalten aufbauen):
`events`/`event_instances`, `service_assignments`, `leaders`,
`congregation_invitations`, `calendar_integrations`, `memberships`,
`planning_slots`, `planning_series`, `export_tokens`, `notifications`.

## Abgleich ORM ↔ Datenbank

`alembic check` läuft in CI **blockierend** (`.github/workflows/alembic-check.yml`):
Jede Abweichung zwischen ORM-Modellen und einer frisch migrierten Datenbank
lässt den Migrations-Check fehlschlagen. Neue Indizes und Constraints gehören
deshalb immer in Migration **und** Modell (`__table_args__`).

Die Datenbank ist dabei die Referenz, weil die Migrationen den tatsächlichen
Stand festlegen. Die frühere Drift (Stand 2026-09-07) ist am 2026-10-01
bereinigt worden:

- Indizes, die nur per Migration existierten, stehen jetzt auch im Modell:
  `congregation_invitations`, `external_event_links` (eindeutig),
  `invitation_overwrite_requests`, `leader_registrations`, `planning_slots`
  (inklusive des partiellen Unique-Index `no_overlapping_planning_slots`).
- `memberships`: Das Modell bildet `uq_memberships_user_role_scope` und den
  kombinierten Index `ix_memberships_scope` ab, statt getrennter Indizes auf
  `scope_type` und `scope_id`.
- `service_assignments.event_id`: Die Spalte ist in der Datenbank `NOT NULL`,
  das Modell jetzt ebenso (vorher fälschlich nullable).
- `users.sub`: Eindeutigkeit über den Constraint `uq_users_sub`; der
  redundante, nicht eindeutige Index `ix_users_sub` entfällt (Migration `0026`).
- `app_superadmin_config` hat bewusst kein ORM-Modell (nur SQL-Funktionen aus
  Migration `0017`) und ist in `alembic/env.py` von der Prüfung ausgenommen.
