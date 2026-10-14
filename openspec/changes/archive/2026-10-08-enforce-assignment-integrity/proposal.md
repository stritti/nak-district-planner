## Why

Issue #468: Die Konfliktprüfung für Dienstzuweisungen war ein ungeschütztes
Check-then-Insert. Zwei parallele Requests konnten denselben Amtsträger doppelt
einplanen, ein Planungseintrag konnte mehrere Zuweisungen halten (die Matrix
zeigte eine beliebige), die Prüfung ließ Termine ohne `EventInstance` stillschweigend
durch (fail-open) und lud die gesamte Historie des Amtsträgers per N+1-Abfragen.
Zusätzlich wurden `congregation_id`/`leader_id` aus Request-Bodies nicht gegen den
Bezirk geprüft, sodass Datensätze anderer Mandanten referenziert werden konnten.

## What Changes

- Unique-Index `ix_service_assignments_planning_slot_id`: höchstens eine Zuweisung
  pro Planungseintrag; Migration `20261007_assignment_unique` bereinigt Altdubletten
  deterministisch (CONFIRMED > ASSIGNED > OPEN, dann verknüpfter Amtsträger, dann
  neueste) und befüllt `planning_slot_id` aus `event_id` nach. Eine zweite Zuweisung
  liefert 409.
- Transaktionsgebundener Advisory-Lock pro `leader_id` um Konfliktprüfung und Insert
  (Wiederverwendung von `app/adapters/db/locks.py`).
- Konfliktprüfung fail-closed: ohne `EventInstance` gilt die geplante Zeit des Slots
  (UTC) plus `SYNC_EXPECTED_DURATION_MINUTES`; abgesagte Slots blockieren nicht.
  Ein einziger, zeitlich gefensterter Join ersetzt die N+1-Abfragen.
- Zentrale Prüfung `app/adapters/api/tenant_references.py`: Gemeinde- bzw.
  Amtsträger-IDs aus Request-Bodies müssen zum Bezirk gehören, sonst 422 mit
  identischer Meldung für unbekannte und fremde IDs (kein Existenz-Orakel; gleiche
  Konvention wie die Gruppenprüfung im Districts-Router). Angewendet auf Export-Tokens,
  Registrierung (Einreichen und Freigabe), Amtsträger (Anlegen/Ändern),
  Planungsserien (Anlegen/Ändern), Gemeinde-Einladungsziel (Anlegen/Ändern) und
  Dienstzuweisungen (Anlegen/Ändern).

## Capabilities

### Modified Capabilities
- `service-assignment`: Eindeutigkeit pro Planungseintrag, serialisierte
  Zuweisung pro Amtsträger, fail-closed Konfliktprüfung, Mandantenprüfung von Referenzen.

## Impact

- Backend: Router `service_assignments`, `export`, `registrations`, `leaders`,
  `planning_series`, `districts`; Repository `SqlServiceAssignmentRepository.list_leader_schedule`;
  neue Alembic-Revision (eine Head).
- Betrieb: Die Migration verschiebt doppelte Zuweisungen in die Archivtabelle
  `service_assignment_duplicates_468` (nur für den Datenbank-Owner lesbar, RLS ohne
  Policy erzwungen); ohne Dubletten entsteht keine Tabelle. Der Downgrade stellt die
  archivierten Zeilen wieder her und entfernt das Archiv. Nach Prüfung kann der
  Betrieb die Tabelle löschen.
