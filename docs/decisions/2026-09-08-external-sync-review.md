# Entscheidung: Externe Sync-Events in v1

**Status:** Akzeptiert für v1

## Entscheidung

Externe Events aus konfigurierten, vertrauenswürdigen ICS-/CalDAV-Quellen werden
direkt übernommen. Ein manueller Review-Workflow mit `ExternalEventCandidate` wird
nicht vor dem v1-Go-Live implementiert.

## Begründung

Der bestehende Sync verwendet `SyncState` und `ExternalEventLink` für
Idempotenz, Hash-Vergleich, Zuordnung und Änderungsverfolgung. Für den v1-Betrieb
mit fachlich freigegebenen Quellen ist ein zusätzlicher Review-Schritt derzeit
nicht erforderlich und würde den Umfang des MVP deutlich vergrößern.

## Konsequenzen

- Quellen dürfen nur durch autorisierte Administratoren konfiguriert werden.
- Neue externe Events werden nach der bestehenden Sync-Logik direkt angelegt oder
  aktualisiert.
- Die Annahme „Quelle ist vertrauenswürdig“ muss gegenüber den Fachverantwortlichen
  dokumentiert und im Betrieb eingehalten werden.
- Ein Review-Workflow für unbekannte Quellen bleibt als Phase 2 offen.
