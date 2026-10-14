# Performance-Baseline

Messungen zu OpenSpec `introduce-non-functional-baseline`, Tasks 3.1 und 3.2.
Test: `services/backend/tests/performance/test_performance_postgres.py`.

## Messaufbau

- Echtes, vollständig migriertes PostgreSQL. Alle Abfragen laufen als Anwendungsrolle `nak_app` (`NOBYPASSRLS`) mit denselben GUCs wie in Produktion. Der RLS-Overhead ist in jeder Messung enthalten.
- Nach dem Seed läuft `ANALYZE` auf den befüllten Tabellen. Ohne Planner-Statistiken schätzt PostgreSQL direkt nach einem Bulk-Insert 1 statt 1300 Zeilen und wählt Nested Loops. Die Latenz hing dann davon ab, wann Autovacuum zuletzt lief (p95 zwischen 230 und 490 ms). In Produktion hält Autovacuum die Statistiken aktuell.
- Die Tests werden übersprungen, solange `RLS_TEST_DATABASE_URL` und `RLS_TEST_APP_PASSWORD` nicht gesetzt sind (gleiche Konvention wie die RLS-Integrationstests).

```bash
cd services/backend
RLS_TEST_DATABASE_URL=postgresql://nak:…@localhost:5432/nak_rls \
RLS_TEST_APP_PASSWORD=… \
uv run pytest tests/performance -s
```

## Matrix-Endpoint (3.1)

Last laut Spec: ein Bezirk mit 50 Gemeinden, Zeitraum 3 Monate (Jan–Mär), Gottesdienste sonntags und mittwochs. Das ergibt 1300 PlanningSlots, zwei Drittel davon mit Zuweisung, dazu 100 Amtsträger. Gemessen wird `GET /api/v1/districts/{id}/matrix` über die ASGI-App inklusive Serialisierung, mit 15 Requests nach einem Warm-up.

| Messung (lokal, PostgreSQL 16) | Wert |
|---|---|
| p50 | ~110 ms |
| p95 | ~230 ms |
| Budget laut Spec (p95) | **≤ 500 ms** |

## Sync-Dauer (3.2)

`run_sync` mit einem statischen Feed aus 500 Events (Connector ersetzt, kein Netzwerk). Unbekannte externe Termine werden seit #376 zu Prüfkandidaten. Der erneute Sync muss alle wiedererkennen und darf keine Duplikate anlegen.

| Messung (lokal) | Wert | Budget |
|---|---|---|
| Erstimport, 500 Events | ~5,5 s | ≤ 12 s |
| Resync ohne Änderungen | ~4,3 s | ≤ 10 s |

Die Budgets liegen bei etwa dem Doppelten der lokalen Werte. Sie dienen als Regressionsschutz auf geteilten CI-Runnern.

### Befund: N+1 im Sync

Der Resync eines unveränderten Feeds ist kaum schneller als der Erstimport (~8,5 ms pro Event). Pro Event laufen einzeln:
- die Link-Suche (`get_by_external_event`),
- die Kandidaten-Suche (`by_external_event`),
- der Slot-Abgleich (`find_exact_matching_slot`),
- das Speichern des Kandidaten.

Mögliche Folgearbeit:
- Links und Kandidaten einer Integration vorab in einem Query laden.
- Unveränderte Kandidaten (gleicher `content_hash`) ohne Slot-Abgleich überspringen.

Bei den heutigen Feed-Größen (einige hundert Termine) liegt der Sync im Minutenraster von Celery Beat deutlich im Rahmen.

## CI

Der CI-Schritt „PostgreSQL integration and performance tests with RLS“ migriert eine leere Datenbank (`alembic upgrade head`, Rollenpasswort zur Laufzeit erzeugt) und führt danach `tests/integration` und `tests/performance` vollständig aus. Übersprungene Tests lassen den Schritt fehlschlagen, weil ein Skip hier nur eine fehlende Datenbank-Einstellung bedeuten kann.
