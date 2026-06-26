# M3 PR #190 — TODO-Abarbeitung

## Goal
Nach dem Legacy-Event-Removal (Phase 1-4, bereits committed + PR #190) die
ausstehenden TODO-Stubs in Routern/Services/Repositories durch echte Logik
mit PlanningSlot/EventInstance ersetzen.

## TODOs nach Scope

### A. `draft_service_generation.py` — PlanningSlot-Erzeugung
- `GenerateDraftServicesUseCase`: `event_repo: None` → `PlanningSlotRepository`
- Für jede Congregation: expanded slots → PlanningSlots prüfen/erstellen
- Für jeden neuen PlanningSlot: EventInstance prüfen/erstellen
- `districts.py` Caller: `event_repo=None` → PlanningSlotRepository

### B. `export.py` — ICS-Kalender-Export
- Refactor von Event-basierter Logik auf PlanningSlot + EventInstance
- Nutze `PlanningSlot.approval_status` statt `Event.approval_status`
- Nutze `EventInstance` für tatsächliche Zeiten

### C. `invitation_service.py` + `routers/invitations.py`
- Komplexester Teil. Invitation-Service nutzt Event-Queries.
- Umstellung auf PlanningSlot/EventInstance für Datenqueries
- `list_open_by_district` im Repository fixen

### D. `service_assignments.py` Router
- Kleine TODOs: `event_id` → `planning_slot_id` in Queries

### E. `tasks.py` — `generate_draft_services_window`
- Reactivate: use updated `GenerateDraftServicesUseCase`

### F. Tests
- Coverage für geänderte Services sicherstellen

## Dependencies
- A muss vor E (tasks.py reactivates draft generation)
- C hängt von keinem anderen (in sich geschlossen)
- B ist unabhängig
- D ist unabhängig

## Phases
1. **Phase 5a:** `draft_service_generation.py` neu schreiben
2. **Phase 5b:** `districts.py` Caller fixen + `tasks.py` reactivate
3. **Phase 6:** `export.py` refactor
4. **Phase 7:** `invitation_service.py` + `routers/invitations.py`
5. **Phase 8:** `service_assignments.py` TODOs
6. **Phase 9:** `invitation_overwrite_request.py` repository fix
7. **Phase 10:** Tests + Coverage
