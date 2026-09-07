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

## Tenant-Scoping (Fremdschlüssel)

Mandantenfähige Tabellen tragen `district_id` und/oder `congregation_id` als
Fremdschlüssel (siehe `docs/security/tenant-isolation.md` für die
RLS-Policies, die auf diesen Spalten aufbauen):
`events`/`event_instances`, `service_assignments`, `leaders`,
`congregation_invitations`, `calendar_integrations`, `memberships`,
`planning_slots`, `planning_series`, `export_tokens`, `notifications`.

## Bekannte Schema-Drift (Stand 2026-09-07)

`alembic check` läuft in CI als **informativer, nicht blockierender** Schritt
(`.github/workflows/alembic-check.yml`), weil aktuell echte Drift zwischen
ORM-Modellen und der migrierten DB besteht — hier dokumentiert, damit sie
nicht mit neuer, durch eine PR eingeführter Drift verwechselt wird:

- Mehrere Indizes existieren in der DB, aber nicht mehr im Modell (fehlendes
  `index=True` bzw. `Index(...)`): `congregation_invitations`,
  `external_event_links`, `invitation_overwrite_requests`,
  `leader_registrations`, `planning_slots`.
- `memberships`: DB hat noch die alte kombinierte
  `uq_memberships_user_role_scope` + `ix_memberships_scope`; das Modell
  definiert stattdessen zwei getrennte Indizes (`ix_memberships_scope_id`,
  `ix_memberships_scope_type`). Die alte Unique-Constraint ist in der DB noch
  aktiv (Verhalten unverändert), nur die Modell-Repräsentation weicht ab.
- `service_assignments.event_id`: Modell verlangt `NOT NULL`, DB-Spalte ist
  noch nullable. **Vor einer Migration prüfen, ob produktiv NULL-Werte
  existieren** — sonst schlägt ein `ALTER COLUMN ... SET NOT NULL` fehl oder
  verletzt Daten.
- `users.ix_users_sub`: DB hat `uq_users_sub` (separate Unique-Constraint) +
  einen nicht-eindeutigen Index gleichen Namens; das Modell erwartet einen
  einzigen eindeutigen Index. Funktional gleichwertig (Eindeutigkeit ist in
  der DB durchgesetzt), nur unterschiedlich repräsentiert.

Reconciliation dieser Punkte ist ein eigener, nicht-trivialer Follow-up
(insbesondere der `event_id`-NOT-NULL-Fall erfordert eine Datenprüfung vor der
Migration) — bewusst nicht Teil dieser Änderung.
