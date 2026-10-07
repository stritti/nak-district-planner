## 1. Eindeutigkeit und Nebenläufigkeit

- [x] 1.1 Migration `20261007_assignment_unique`: `planning_slot_id` aus `event_id` nachbefüllen, Dubletten deterministisch auflösen, Unique-Index anlegen (Downgrade: nicht eindeutiger Index)
- [x] 1.2 ORM `ServiceAssignmentORM.planning_slot_id` als `unique=True` deklarieren (`alembic check` ohne Drift)
- [x] 1.3 Router: `IntegrityError` beim Speichern → 409
- [x] 1.4 Advisory-Lock pro `leader_id` vor Konfliktprüfung (Anlegen und Ändern)

## 2. Konfliktprüfung

- [x] 2.1 `ScheduledService.window()`: Ist-Zeiten oder geplante Zeit + Standarddauer (fail-closed)
- [x] 2.2 `list_leader_schedule`: ein gefensterter Join statt N+1, nur aktive Slots
- [x] 2.3 Unit-Tests für Fallback, Fenster und Einzelabfrage

## 3. Mandantenprüfung von Referenzen

- [x] 3.1 Zentrale Hilfsfunktionen `ensure_congregation_in_district` / `ensure_leader_in_district` (422, einheitliche Meldung)
- [x] 3.2 Anwenden auf Export-Tokens, Registrierung (Einreichen, Freigabe), Amtsträger, Planungsserien, Einladungsziel der Gemeinde, Dienstzuweisungen
- [x] 3.3 Negativtests pro Endpunkt

## 4. Verifikation

- [x] 4.1 PostgreSQL-Integrationstest mit zwei parallelen Sessions (Doppelbuchung, zweite Zuweisung pro Slot)
- [x] 4.2 Integrationstest der Dubletten-Auflösung der Migration
