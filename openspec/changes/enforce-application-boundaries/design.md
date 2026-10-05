## Context

Das Backend ist als Domain/Application/Adapter-Struktur angelegt. Im historischen Application-Layer existieren jedoch noch direkte Adapter- und SQLAlchemy-Imports, insbesondere in Task-Orchestrierung und einzelnen Services. Ein RC-2-Blocker ist nicht deren sofortige vollstaendige Migration, sondern das Fehlen einer technischen Grenze gegen neue Verstösse.

## Decision

### 1. Architekturgrenze als AST-Test

`tests/unit/test_architecture_boundaries.py` parst alle Python-Dateien direkt unter `app/application` mit `ast` und erkennt Importziele ohne Module auszufuehren.

Verboten fuer neue Application-Module sind:

- Module unter `app.adapters.*`
- direkte `sqlalchemy*`-Imports

Damit bleibt der Test schnell, deterministisch und unabhaengig von Runtime-Konfiguration oder Datenbankverbindungen.

### 2. Explizite Legacy-Allowlist

Bestehende Verstösse werden auf Dateiebene in zwei unveraenderlich gedachten Mengen dokumentiert. Die Tests schlagen fehl, wenn:

- ein neues Modul eine verbotene Abhaengigkeit einfuehrt,
- ein nicht gelistetes bestehendes Modul eine solche Abhaengigkeit erhaelt,
- oder ein gelistetes Modul die Abhaengigkeit nicht mehr besitzt und daher aus der Allowlist entfernt werden kann.

Die Allowlist ist damit eine Debt-Baseline, keine Erweiterungsschnittstelle.

### 3. Zielrichtung fuer neue Application-Services

Neue Use Cases und Services beziehen Repositories, Mail, Kalender, IDP oder andere Infrastruktur ueber Ports/Interfaces im Domain-Layer. Adapter implementieren diese Ports und werden an den Composition Roots verdrahtet.

### 4. Eine kanonische Versionsquelle

Die FastAPI-Metadaten verwenden `settings.app_version`. Dieselbe Eigenschaft basiert auf der installierten Paketversion und wird bereits von Health-/Versionsendpunkten verwendet. Dadurch kann OpenAPI nicht mehr mit einer hardcodierten Altversion divergieren.

### 5. Dokumentation ist Teil des RC-Gates

Runbook, Architektur- und Security-Status beschreiben nur Mechanismen, die im RC-2-Code tatsaechlich existieren. Erledigte OpenSpec-Deltas werden archiviert, aktive Deltas bleiben unter `openspec/changes/`.

## Alternatives Considered

### Vollstaendiger Port/Adapter-Umbau vor RC-2

Verworfen fuer diesen PR: zu grosser fachlicher und operativer Change kurz vor dem Release Candidate. Die technische Grenze verhindert neue Verschlechterungen und erlaubt danach kleine, einzeln reviewbare Migrationen.

### Import-Linter als neue Drittanbieter-Abhaengigkeit

Nicht erforderlich. Die benoetigte Regel ist klein genug fuer die Python-Standardbibliothek `ast`; eine neue Build-Abhaengigkeit wuerde fuer eine einzelne Regel mehr Supply-Chain- und Wartungsaufwand erzeugen.

## Migration Path

1. RC-2 friert die aktuelle Debt-Baseline ein.
2. Nachfolgende PRs verschieben je einen Legacy-Service hinter bestehende oder neue Domain-Ports.
3. Mit jeder Migration wird der zugehoerige Allowlist-Eintrag entfernt.
4. Zielzustand ist eine leere Allowlist.
