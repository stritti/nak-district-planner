## Kontext

Gottesdienste werden im Datenmodell als `PlanningSlot` mit `category="Gottesdienst"`
repräsentiert — dieselben Objekte, die auch die Matrix (UC-03) befüllen. Die
Event-Übersicht (`GET /api/v1/events`, `EventListView.vue`) zeigt alle Slots, trennt
aber nicht zwischen Gottesdiensten und anderen Ereignissen (z. B. `Feiertag`,
`Andacht`, Konzer-Events). Die Kategorie ist bislang nur ein Freitext-Feld ohne
Filteroption.

Die Kennzeichnung "Gottesdienst" ist im System bereits eine etablierte Konvention:

- Matrix-Lücken-Logik: `category=Gottesdienst AND ServiceAssignment=NULL` (UC-03)
- Serien-Generierung: `category=series.category or "Gottesdienst"`
  (`planning_series_service.py`)
- Entwurfs-Generierung: `category="Gottesdienst"`
  (`draft_service_generation.py`)
- Bezirks-Router: `slot.category == "Gottesdienst"` (`districts.py`)

## Ziele / Nicht-Ziele

**Ziele:**

- Gottesdienste in der Event-Übersicht visuell eindeutig als solche erkennbar machen.
- Serverseitigen Filter bereitstellen, damit Pagination (`total`) und Excel-Export
  die gefilterte Menge korrekt abbilden.
- Eine einzige, zentrale Definition dessen, was ein Gottesdienst ist (Backend), statt
  verstreuter String-Vergleiche im Frontend.

**Nicht-Ziele:**

- Änderungen an der Matrix-Ansicht oder der Lücken-Logik (UC-03 bleibt unverändert).
- Neue DB-Spalte oder Migration — `category` bleibt der Wahrheitsgehalt.
- Normalisierung/Validierung der Kategorie-Ausprägungen (beliebige Freitext-Kategorien
  bleiben erlaubt).
- Änderung des Excel-Exports (nutzt bereits `category`).

## Entscheidungen

### 1. `is_service` als berechnetes Feld statt neues DB-Feld

**Entscheidung:** Das Backend ergänzt `EventResponse` um ein berechnetes Feld
`is_service: bool` mit `is_service = (slot.category == "Gottesdienst")`. Kein
DB-Schema-Wandel.

**Begründung:** Die Kategorie ist bereits der etablierte Wahrheitsgehalt für
Gottesdienste (siehe Kontext). Ein zusätzliches DB-Feld würde zwei Wahrheitsquellen
erzeugen und eine Migration erfordern. Die Prüfung `category == "Gottesdienst"` wird im
Router an einer Stelle zentral gekapselt, statt im Frontend verstreut String-Vergleiche
zu pflegen.

**Alternativen:** (a) Frontend leitet `is_service` selbst aus `category` ab — verworfen,
weil die Definition dann an vielen Stellen dupliziert wird; (b) neue boolean
DB-Spalte — verworfen wegen Doppel-Wahrheitsquelle und unnötiger Migration.

### 2. Query-Parameter `is_service` (boolean, tri-state)

**Entscheidung:** `GET /api/v1/events?is_service=true|false`. `true` → nur Slots mit
`category="Gottesdienst"`; `false` → alle Slots mit anderer oder leerer Kategorie;
nicht gesetzt → kein Filter (Rückwärtskompatibilität).

**Begründung:** Ein boolescher Parameter deckt beide Nutzungsrichtungen ab ("nur
Gottesdienste" und "nur andere Ereignisse") und filtert vor der Pagination, sodass
`total` korrekt ist. Die Filterung erfolgt wie die bestehenden Status-Filter
in-memory nach `list_for_date_range` — konsistent mit dem bestehenden Router-Muster,
kein Repository-Änderung nötig.

### 3. Frontend-Filter-Dropdown "Typ"

**Entscheidung:** Ein Select `Alle / Gottesdienste / Andere Ereignisse` in der
bestehenden Filter-Leiste (zwischen "Freigabe" und den Datumsfeldern). Der Filter gilt
für alle drei Ansichtsmodi (Liste, Woche, Monat), analog zu Status/Freigabe.

**Begründung:** Konsistent mit den bestehenden Filtern; week/month rufen dieselbe API
mit denselben Parametern auf.

### 4. Visuelle Kennzeichnung

**Entscheidung:** Dediziertes "Gottesdienst"-Badge (blau, `bg-blue-100 text-blue-800`)
in Listen-Tabelle und mobilen Karten, zusätzlich zur Kategorie-Anzeige. In Woche/Monat
behalten Gottesdienst-Pills die bestehende blaue Färbung; andere Events bleiben grau.

**Begründung:** Die blaue Farbe ist bereits als Gottesdienst-Assoziation etabliert
(`eventPillClass`). Das Badge macht die Kennzeichnung in der Liste explizit, ohne die
Kategorie-Spalte zu ersetzen.

## Risiken / Trade-offs

- String-Vergleich `"Gottesdienst"` bleibt Konvention (kein Enum). Bestehende Daten mit
  abweichender Schreibung (z. B. Tippfehler) würden nicht als Gottesdienst erkannt —
  identisches Risiko wie heute in Matrix und Generierungs-Logik; durch die zentrale
  Konstante künftig einfach korrigierbar.
- In-memory-Filterung über alle Slots des Zeitraums: identisches Performance-Profil wie
  die bestehenden Status-Filter (kein zusätzlicher DB-Roundtrip).
