## 1. Implementierung
- [x] 1.1 `matrix_conflicts` um weitere Buchungen je Amtsträger und Abwesenheiten erweitern (`leader_available`), eigene Slot-Buchung ignorieren
- [x] 1.2 `list_overlapping_for_leaders` im Port und im SQL-Repository
- [x] 1.3 Matrix-Builder und Router: Dienst-Lookup je zugewiesenem Amtsträger und Abwesenheiten in einer Abfrage

## 2. Tests
- [x] 2.1 Unit-Tests der Domänenfunktion (Dienst überlappend, Wechselzeit, eigener Slot, anderer Amtsträger, Abwesenheit)
- [x] 2.2 Router-Tests der Matrix (Dienst, eigener Slot, Abwesenheit, keine Lookups ohne Zuweisung)
- [x] 2.3 PostgreSQL-Tests: Abwesenheiten mit RLS, fremder Bezirk, Dienst-Lookup mit Platzhalter, Viewer ohne Dienste
