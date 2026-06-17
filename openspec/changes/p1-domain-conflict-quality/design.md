## Context

Der NAK District Planner hat eine funktionierende Event- und ServiceAssignment-Verwaltung. Was fehlt, ist eine fachliche Prüfebene, die Planungskonflikte erkennt. Aktuell können:

- Ein Amtsträger in zwei gleichzeitigen Gottesdiensten eingeplant werden
- Direkt aufeinanderfolgende Termine in räumlich getrennten Gemeinden zugewiesen werden
- Dienste an Amtsträger vergeben werden, die die erforderliche Amtsstufe nicht haben
- Amtsträger trotz Urlaub/Abwesenheit eingeplant werden

Die bestehende Hexagonal-Architektur erlaubt die Implementierung als reines Domain-Service ohne Framework-Anhängigkeiten.

## Goals / Non-Goals

**Goals:**
- Ein Amtsträger kann nicht zeitgleich in mehreren Events eingeplant werden.
- Ein Amtsträger kann nicht in zwei räumlich getrennten Gemeinden direkt nacheinander ohne konfigurierbare Wechselzeit eingeplant werden.
- Bestimmte Dienste erfordern bestimmte Rollen/Amtsstufen (konfigurierbar).
- Urlaube, Abwesenheiten und Sperrzeiten werden bei der Zuweisung berücksichtigt.
- Konflikte werden im Frontend sichtbar gemacht (Matrix-Ansicht + Zuweisungsdialog).
- E2E-Tests decken die drei kritischen Planungsflows ab.

**Non-Goals:**
- Keine automatische Konfliktlösung – der Planer entscheidet bei WARN-Konflikten.
- Keine Optimierungsengine – der Service zeigt Konflikte, löst sie nicht selbst.
- Keine Integration mit externen Kalendern für Abwesenheiten (zunächst manuelle Eingabe).
- Kein ABAC – die Regeln bleiben deklarativ, nicht attributbasiert.

## Decisions

### Decision 1: Conflict Engine als reiner Domain Service

**Entscheidung:** Die Konfliktengine lebt in `domain/planning/` und importiert kein Framework (kein FastAPI, kein SQLAlchemy). Sie arbeitet auf Domain-Modellen, die der Aufrufer (Application/Use-Case-Layer) bereitstellt.

```text
domain/planning/
  conflict_rules.py    # Einzelne Prüfregeln (jede ist eine reine Funktion)
  conflict_service.py  # Orchestrierung: führt alle Regeln aus, sammelt Ergebnisse
  conflict_result.py   # Result-Typ: PASS | WARN | BLOCK + Nachricht + Metadaten
```

**Alternative:** Integration in Application Services.
**Rationale:** Reine Domain-Logik ist testbar, framework-unabhängig und kann auch in Celery-Tasks oder CLI-Tools verwendet werden.

### Decision 2: Rule-Engine mit deklarativen Regeln

**Entscheidung:** Jede Konfliktregel implementiert ein einfaches Protocol:

```python
class ConflictRule(Protocol):
    def __call__(self, context: ConflictContext) -> ConflictResult | None: ...
```

Regeln sind unabhängige Funktionen in `conflict_rules.py`:

| Regel | Prüfung | Ergebnis bei Verletzung |
|-------|---------|------------------------|
| `no_double_booking` | Amtsträger hat zum Zeitpunkt bereits eine Zuweisung | BLOCK |
| `travel_time_check` | Zwei Zuweisungen in verschiedenen Gemeinden haben < `min_travel_minutes` Abstand | WARN |
| `role_requirement_check` | Der zugewiesene Dienst erfordert eine bestimmte Amtsstufe | BLOCK |
| `leader_available` | Amtsträger hat im Zeitraum eine `leader_unavailability` | BLOCK |
| `congregation_distance_check` | Zuweisungen in verschiedenen Gemeinden erfordern expliziten Vermerk | WARN |

### Decision 3: Integration via Application Service

**Entscheidung:** Die Application Services (`event_service.py`, `service_assignment_service.py`) rufen `conflict_service.check()` vor dem Speichern auf:

```python
conflicts = conflict_service.check(
    leader_id=leader_id,
    start_time=event.start,
    end_time=event.end,
    congregation_id=event.congregation_id,
    required_role=event.required_leader_role,
    existing_assignments=existing_assignments,
    unavailability_periods=leader_unavailability periods,
)
if any(c.severity == Severity.BLOCK for c in conflicts):
    raise ConflictError(conflicts)
# else: save with optional WARN annotations
```

### Decision 4: Abwesenheiten als eigene Entität

**Entscheidung:** `LeaderUnavailability` wird als eigenes Domain-Modell + ORM-Modell + Migration umgesetzt.

```python
class LeaderUnavailability:
    id: UUID
    leader_id: UUID
    start_date: datetime
    end_date: datetime
    reason: str  # URLAUB, SPRERRZEIT, FORTBILDUNG, SONSTIGES
    note: str | None
```

### Decision 5: Frontend-Konfliktanzeige als modaler Layer

**Entscheidung:** Das Frontend zeigt Konflikte im Zuweisungsdialog und in der Matrix-Ansicht. Bei BLOCK-Konflikten wird die Aktion verhindert (Button deaktiviert + Tooltip/Modal mit Konfliktgründen). Bei WARN-Konflikten erscheint ein Bestätigungsdialog.

**Kein** automatisches Wegklicken von WARN-Konflikten – der Planer muss aktiv bestätigen.

### Decision 6: E2E-Tests für Planungsflows

**Entscheidung:** Playwright-Tests decken ab:
1. Gottesdienst planen → Amtsträger zuweisen → Bestätigung
2. Double-Booking provozieren → BLOCK-Konflikt wird angezeigt
3. Wechselzeit-Konflikt provozieren → WARN-Konflikt mit Bestätigungsdialog
4. Abwesenheit erfassen → Zuweisung blockiert

## Risks / Trade-offs

- [Conflict Service erhöht Latenz bei Event-Erstellung] → Rules sind reine Funktionen, die im Millisekunden-Bereich liegen. DB-Queries für bestehende Zuweisungen sind der relevante Teil.
- [Zu strenge Regeln frustrieren Planer] → Jede Regel hat einen konfigurierbaren Schweregrad (BLOCK/WARN). Produktivstart mit WARN, später auf BLOCK verschärfen.
- [Abwesenheiten müssen manuell gepflegt werden] → Zunächst MVP, später Integration mit externen Kalendern.
- [E2E-Tests sind wartungsintensiv] → Fokus auf die drei kritischen Flows, nicht auf jede UI-Variante.

## Migration Plan

1. `conflict_rules.py` mit den fünf Kernregeln implementieren.
2. `conflict_service.py` als Orchestrator implementieren.
3. `LeaderUnavailability`-Domain-Modell + Migration + Repository.
4. Integration in `service_assignment_service.py` und `event_service.py`.
5. Unit-Tests für jede Regel + Integrationstests für den Service.
6. Frontend-Konfliktanzeige: neues `ConflictBanner`-Component, Integration in Matrix-View und Assignment-Dialog.
7. Frontend-Abwesenheitsverwaltung: Formular + Liste für Leader-Unavailabilities.
8. Playwright-E2E-Tests für die drei Planungsflows.
9. Validierung bestehender Frontend-Formulare (onSubmit + inline).

Rollback: Conflict-Check per Feature-Flag deaktivierbar (`CONFLICT_CHECK_ENABLED=false`). Unveränderte Events bleiben erhalten.
