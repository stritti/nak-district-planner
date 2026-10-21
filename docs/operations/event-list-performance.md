# Ereignisliste: PostgreSQL Query-Plan-Baseline (#626)

Stand: 18.10.2026. Messung mit PostgreSQL 18.6 unter GitHub Actions, CI-Run [39168157608](https://github.com/stritti/nak-district-planner/actions/runs/39168157608), Artefakt `event-list-query-plans` (vollständiges `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`).

## Wiederholbare Testlast

`tests/performance/test_event_listing_query_plans.py` erzeugt in einem isolierten, migrierten Testsystem 50.000 Planungs-Slots über 25 Gemeinden in einem Bezirk sowie 1.000 fremde Slots. Die Zeitverteilung, Kategorien, Status, anwendbare Bezirksereignisse und Offsetwerte sind reproduzierbar definiert. Die IDs werden pro Testlauf neu erzeugt. Die Testdaten werden mit dem Owner-DSN angelegt und mit `ANALYZE` erfasst; gemessen wird als Bezirksplaner über die `NOBYPASSRLS`-Anwendungsrolle (`nak_app`), also mit den RLS-Prädikaten der Produktion. Die Tests verwenden `SqlPlanningSlotRepository.list_page()` und zeichnen die **tatsächlich ausgeführten** Count- und Page-SQL-Statements auf; jedes wird mit unveränderten Bind-Parametern nach sechs unprotokollierten Läufen (über den Wechsel auf generische Pläne hinaus) fünfmal mit `EXPLAIN (ANALYZE, BUFFERS)` gemessen (Median und Maximum im Artefakt). Jede Seite muss voll sein, und eine Abfrage des Planers auf den fremden Bezirk muss unter RLS leer bleiben. Eine `statement_timeout` von 10 Sekunden auf der Messverbindung begrenzt jede Abfrage einschließlich des ersten `list_page()`-Aufrufs. Alle Testdaten werden anschließend entfernt und die Tabelle per `VACUUM ANALYZE` bereinigt, damit nachfolgende Performance-Tests nicht auf einer aufgeblähten Tabelle laufen.

## Beobachtungen

### Tabelleneigentümer ohne RLS (18.10.2026, PostgreSQL 18.6, CI)

Diese erste Messung lief als Tabelleneigentümer und damit **ohne** RLS. Sie zeigt die Indexnutzung, nicht die Produktionslatenz.

| Filter | Treffer | Count [ms] | 500er Seite [ms] | Count Shared Hit Blocks | Page Shared Hit Blocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bezirk, Offset 0 | 50.000 | 18,275 | 0,860 | 50.052 | 550 |
| Bezirk, Offset 10.000 | 50.000 | 18,094 | 13,965 | 50.052 | 10.562 |
| Gemeinde mit `applicability` | 14.000 | 20,682 | 1,225 | 50.051 | 1.785 |
| Nur Bezirkstermine | 12.500 | 18,953 | 1,261 | 50.051 | 2.062 |

Alle vier Abfragen verwendeten `ix_planning_slots_district_date`. Die Seitenabfrage benutzte eine `Index Scan`-Operation mit `Incremental Sort`; der Count-Pfad war je nach Filter `Index Scan` oder `Index Only Scan`. Der reine Bezirks-Count verursachte trotz `Index Only Scan` 50.000 Heap Fetches, da die synthetischen Zeilen unmittelbar vor der Messung geschrieben wurden (Visibility Map noch nicht aufgefrischt). Diese Kosten dürfen nicht ohne weiteres auf autovacuum-gepflegte Produktivtabellen übertragen werden.

### Anwendungsrolle mit RLS (20.10.2026, PostgreSQL 16, lokal)

Median aus fünf Messungen. Die verbindliche Messung liefert das CI-Artefakt auf PostgreSQL 18.

| Filter | Treffer | Count JIT an [ms] | Count JIT aus [ms] | 500er Seite JIT aus [ms] |
| --- | ---: | ---: | ---: | ---: |
| Bezirk, Offset 0 | 50.000 | 911 | 55 | 1,6 |
| Bezirk, Offset 10.000 | 50.000 | 881 | 34 | 27 |
| Gemeinde mit `applicability` | 14.000 | 89 | 12 | 2,0 |
| Nur Bezirkstermine | 12.500 | 71 | 9 | 1,4 |

Die RLS-Policy erweitert den Plan um gehashte Mitgliedschafts-Subplans; der Index bleibt aktiv. Mit eingeschaltetem JIT übersteigt die Kostenschätzung des Bezirks-Counts `jit_above_cost`, und rund 730 ms der 760 ms entfallen auf JIT-Kompilierung, die PostgreSQL bei jeder Ausführung neu bezahlt. Ohne JIT bleibt der RLS-Pfad im zweistelligen Millisekundenbereich.

## Entscheidungen

- **Index:** Der vorhandene Bezirk/Datum-Index ist im beobachteten Lastfall aktiv. Ein zusätzlicher GIN-Index für `applicability` ist **nicht durch diese Messung gerechtfertigt**. Die Gemeindeabfrage verarbeitet die OR/ANY-Verzweigung ohne RLS in rund 21 ms, mit RLS (JIT aus) in rund 12 ms für den Count; bei wesentlich größeren oder anders verteilten Datensätzen separat messen.
- **Pagination:** `limit/offset` bleibt unverändert; ein API- und Frontend-brechender Wechsel zu Keyset-Pagination ist bei den gemessenen 14 ms (ohne RLS) bzw. 27 ms (mit RLS, JIT aus) für Offset 10.000 nicht erforderlich. Die bereits vorhandene 10.000er Obergrenze bleibt.
- **JIT:** Ob `jit` für die Anwendungsrolle abgeschaltet oder `jit_above_cost` angehoben wird, ist eine Betriebsentscheidung. Vorher die CI-Pläne auf PostgreSQL 18 und reale Produktionspläne prüfen; diese Messung ändert die Datenbankkonfiguration nicht.
- **Statement-Timeout:** Im Performance-Test 10 Sekunden auf der Messverbindung. Eine globale Produktionsänderung erfolgt ohne reale Betriebsdaten nicht, um längere zulässige Operationen nicht unbeabsichtigt abzubrechen.
- **Betrieb:** Query-Latenz, Count-Latenz, Sequential Scans und Index-/Heap-Buffer im Monitoring beobachten. Bei Wachstum/abweichenden Filtern zuerst Statistik/VACUUM und aktuelle `EXPLAIN`-Pläne prüfen, dann eine separate OpenSpec-Index- oder Keyset-Änderung formulieren.

## Evidenzgrenzen und offene Verifikation

Das sind Werte synthetischer Testdaten mit fünf Wiederholungen je Abfrage, keine Produktions-SLOs und keine p95/p99-Latenzen. Nicht erfasst sind konkurrierende Nutzerlast, Cold-Cache-Verhalten, Datenwachstum über 50.000 Slots, Produktions-I/O und Langzeitstatistiken. Die übrigen Filterkombinationen sind in `tests/integration/test_event_listing_postgres.py` gegen die bisherigen Filtersemantiken abgesichert; der Lasttest fokussiert die vier teuren Ausprägungen. Eine reale Produktions-Query-Plan-Prüfung bleibt vor größeren Optimierungen erforderlich.

Die Tests sind über die bestehende PostgreSQL-CI integriert und ihre vollständigen Pläne als Artefakt abrufbar.
