# Ereignisliste: PostgreSQL Query-Plan-Baseline (#626)

Stand: 18.10.2026. Messung mit PostgreSQL 18.6 unter GitHub Actions, CI-Run [39168157608](https://github.com/stritti/nak-district-planner/actions/runs/39168157608), Artefakt `event-list-query-plans` (vollständiges `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`).

## Wiederholbare Testlast

`tests/performance/test_event_listing_query_plans.py` erzeugt in einem isolierten, migrierten Testsystem 50.000 Planungs-Slots über 25 Gemeinden in einem Bezirk sowie 1.000 fremde Slots. Die Zeitverteilung, Kategorien, Status, anwendbare Bezirksereignisse und Offsetwerte sind reproduzierbar definiert. Die IDs werden pro Testlauf neu erzeugt. Die Tests verwenden `SqlPlanningSlotRepository.list_page()` und zeichnen die **tatsächlich ausgeführten** Count- und Page-SQL-Statements auf; beide werden mit unveränderten Bind-Parametern analysiert. Eine lokal gesetzte `statement_timeout` von 10 Sekunden schützt den Test. Alle Testdaten werden anschließend entfernt.

## Beobachtungen

| Filter | Treffer | Count [ms] | 500er Seite [ms] | Count Shared Hit Blocks | Page Shared Hit Blocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bezirk, Offset 0 | 50.000 | 18,275 | 0,860 | 50.052 | 550 |
| Bezirk, Offset 10.000 | 50.000 | 18,094 | 13,965 | 50.052 | 10.562 |
| Gemeinde mit `applicability` | 14.000 | 20,682 | 1,225 | 50.051 | 1.785 |
| Nur Bezirkstermine | 12.500 | 18,953 | 1,261 | 50.051 | 2.062 |

Alle vier Abfragen verwendeten `ix_planning_slots_district_date`. Die Seitenabfrage benutzte eine `Index Scan`-Operation mit `Incremental Sort`; der Count-Pfad war je nach Filter `Index Scan` oder `Index Only Scan`. Der reine Bezirks-Count verursachte trotz `Index Only Scan` 50.000 Heap Fetches, da die synthetischen Zeilen unmittelbar vor der Messung geschrieben wurden (Visibility Map noch nicht aufgefrischt). Diese Kosten dürfen nicht ohne weiteres auf autovacuum-gepflegte Produktivtabellen übertragen werden.

## Entscheidungen

- **Index:** Der vorhandene Bezirk/Datum-Index ist im beobachteten Lastfall aktiv. Ein zusätzlicher GIN-Index für `applicability` ist **nicht durch diese Messung gerechtfertigt**. Die Gemeindeabfrage verarbeitet die OR/ANY-Verzweigung in rund 21 ms für den Count; bei wesentlich größeren oder anders verteilten Datensätzen separat messen.
- **Pagination:** `limit/offset` bleibt unverändert; ein API- und Frontend-brechender Wechsel zu Keyset-Pagination ist bei den gemessenen 14 ms für Offset 10.000 nicht erforderlich. Die bereits vorhandene 10.000er Obergrenze bleibt.
- **Statement-Timeout:** Im Performance-Test `SET statement_timeout TO '10s'`. Eine globale Produktionsänderung erfolgt ohne reale Betriebsdaten nicht, um längere zulässige Operationen nicht unbeabsichtigt abzubrechen.
- **Betrieb:** Query-Latenz, Count-Latenz, Sequential Scans und Index-/Heap-Buffer im Monitoring beobachten. Bei Wachstum/abweichenden Filtern zuerst Statistik/VACUUM und aktuelle `EXPLAIN`-Pläne prüfen, dann eine separate OpenSpec-Index- oder Keyset-Änderung formulieren.

## Evidenzgrenzen und offene Verifikation

Das sind Werte **eines** CI-Laufs auf synthetischen Testdaten, keine Produktions-SLOs und keine p95/p99-Latenzen. Nicht erfasst sind konkurrierende Nutzerlast, Cold-Cache-Verhalten, Datenwachstum über 50.000 Slots, Produktions-I/O und Langzeitstatistiken. Die übrigen Filterkombinationen sind in `tests/integration/test_event_listing_postgres.py` gegen die bisherigen Filtersemantiken abgesichert; der Lasttest fokussiert die vier teuren Ausprägungen. Eine wiederholte Messreihe sowie eine reale Produktions-Query-Plan-Prüfung bleiben vor größeren Optimierungen erforderlich.

Die Tests sind über die bestehende PostgreSQL-CI integriert und ihre vollständigen Pläne als Artefakt abrufbar.
