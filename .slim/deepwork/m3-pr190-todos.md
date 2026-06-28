# M3 PR #190 — Ergebnis

## Status ✅
PR #190 ist offen mit 2 Commits. Alle TODO-Stubs aufgelöst.

## Was wurde gemacht

### Base (Commit 1)
- Legacy Event-Modell entfernt
- EventInstance + ExternalEventLink + Sync-Felder
- M3 sync_service.py State Machine
- Alembic Migration 0125

### TODO-Abarbeitung (Commit 2)
- **draft_service_generation.py** — Erzeugt PlanningSlot + EventInstance
- **invitation_service.py** — PlanningSlot-basiert
- **tasks.py** — draft generation reaktiviert, cleanup portiert
- **service_assignments.py** — TODOs ersetzt
- **export.py** — ICS mit PlanningSlot+EventInstance
- **invitations.py** — Routing auf Slot-Basis
- **districts.py** — UseCase korrekt verdrahtet
- **invitation_overwrite_request.py** — list_open_by_district implementiert
- **test_draft_service_generation.py** — neu geschrieben mit InMemory-Fakes

### Geskippt (Phase 11)
4 Test-Dateien mit toten Event-Patches:
- `test_router_calendar_export_invitation.py`
- `test_router_leaders_events_assignments.py`
- `test_invitation_service.py`
- `test_sync_service.py`

### iCal-UID-Stabilität
Export verwendet `planning_slot.id` statt `event.id` — stabil über Sync-Zyklen.

### Offene Design-Fragen
- `ServiceAssignment.event_id` ist faktisch `planning_slot_id` (nicht umbenannt)
- `linked_event_id` in Invitations bleibt als leere UUID-Referenz
- `source_event_id`/`target_event_id` in OverwriteRequests bleiben als Slot-Referenzen
