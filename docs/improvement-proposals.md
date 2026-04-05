# Verbesserungsvorschläge – Analyse & Plan

Dieses Dokument enthält eine strukturierte Analyse des NAK District Planners auf Basis der
OpenSpec-Spezifikationen. Es identifiziert Vereinfachungspotenziale, architektonische Lücken,
Refactoring-Möglichkeiten sowie UX-Verbesserungen und dient als Planungsgrundlage für die
Weiterentwicklung.

> **Status:** Entwurf – Stand April 2026  
> **Basis:** OpenSpec-Änderungen `uc-01` bis `uc-06`, `planning-slot-hybrid-sync`,
> `introduce-rbac-permissions-model`, `harden-calendar-sync-algorithm`,
> `introduce-non-functional-baseline`, `phase4b-oidc-auth-idp-agnostic`

---

## 1. Implementierungsstand vs. Spezifikation

### Überblick

| Feature | Spezifiziert | Implementiert | Anmerkung |
|---------|:---:|:---:|-----------|
| OAuth/OIDC-Login | ✅ | ✅ | Phase 4b vollständig, provider-agnostisch |
| Bezirk & Gemeinde (CRUD) | ✅ | ✅ | Inkl. Hierarchie |
| Event-CRUD | ✅ | ✅ | Phase-1-Refactor geplant |
| Kalender-Integration (ICS/CalDAV) | ✅ | ✅ | Voll funktionsfähig |
| Kalender-Integration (Google/Microsoft) | ✅ | 🟡 | Nur Stubs – OAuth-Flows ausstehend |
| Zyklischer Sync (Celery) | ✅ | ✅ | Hash-basierte Deduplizierung |
| Dienstplanung-Matrix | ✅ | ✅ | Inkl. LÜCKE-Visualisierung & Modal |
| Feiertags-Import | ✅ | ✅ | Nager.Date + Gauss-Algorithmus |
| ICS-Export (Token-basiert) | ✅ | ✅ | Stabile UIDs, PUBLIC/INTERNAL |
| Event-Verteilung (applicability) | ✅ | ✅ | Virtuell, keine Duplizierung |
| **PlanningSlot / PlanningSeries** | ✅ | ❌ | Phase 1 – kritisches Fundament |
| **EventInstance (Soll/Ist)** | ✅ | ❌ | Phase 1 – Abhängigkeit von PlanningSlot |
| **ExternalEventCandidate & Review** | ✅ | ❌ | Phase 1 |
| **RBAC-Durchsetzung** | ✅ | 🟡 | Modelle vorhanden, Guards unvollständig |
| **Sync-Zustandsmaschine (Harden)** | ✅ | ❌ | Phase 4 – abhängig von Phase 1 |
| **ExternalEventLink** | ✅ | ❌ | Phase 3 |
| **In-App-Benachrichtigungen** | ✅ | ❌ | Phase 1 |
| **Rate-Limiting (public Endpoints)** | ✅ | ❌ | Phase 5 |
| **Audit-Logging (vollständig)** | ✅ | 🟡 | Infrastruktur vorhanden, nicht umfassend |
| **Performance-Monitoring / SLOs** | ✅ | ❌ | Phase 5 |

---

## 2. Vereinfachungspotenziale

### 2.1 Connector-Factory im Sync-Service

**Aktuell:** Die Funktion `_get_connector()` in `sync_service.py` enthält eine manuelle
`if/elif`-Kette für jeden Kalender-Typ.

```python
def _get_connector(calendar_type: CalendarType) -> CalendarConnector:
    if calendar_type == CalendarType.ICS:
        return ICalConnector()
    elif calendar_type == CalendarType.GOOGLE:
        return GoogleCalendarConnector()
    ...
```

**Vereinfachung:** Die Zuordnung kann als Klassen-Registry direkt am `CalendarType`-Enum oder
als Dictionary definiert werden. So entfällt die manuelle Pflege der Factory bei neuen Providern.

```python
_CONNECTOR_MAP: dict[CalendarType, type[CalendarConnector]] = {
    CalendarType.ICS: ICalConnector,
    CalendarType.GOOGLE: GoogleCalendarConnector,
    ...
}

def _get_connector(calendar_type: CalendarType) -> CalendarConnector:
    cls = _CONNECTOR_MAP.get(calendar_type)
    if cls is None:
        raise NotImplementedError(f"No connector for {calendar_type}")
    return cls()
```

**Aufwand:** Sehr gering. **Priorität:** Niedrig.

---

### 2.2 OAuth-Stubs (Google, Microsoft) klar kennzeichnen

**Aktuell:** `GoogleCalendarConnector` und `MicrosoftGraphCalendarConnector` existieren als
fast leere Stubs ohne deutliche Warnung.

**Vereinfachung:** Entweder die Stubs mit expliziten `NotImplementedError`-Nachrichten versehen
und in der UI deaktivieren, oder als Platzhalter im Integrations-Formular mit dem Badge
„Coming soon" kennzeichnen.

**Aufwand:** Gering. **Priorität:** Mittel – verhindert Verwirrung bei Nutzern und Entwicklern.

---

### 2.3 Celery-Async-Bridge dokumentieren

**Aktuell:** Celery-Tasks rufen `asyncio.run()` auf, um async-Anwendungslogik synchron
auszuführen. Dieses Bridge-Pattern ist bewusst gewählt, aber nicht dokumentiert.

**Vereinfachung:** Einen kurzen Kommentar im Task-Code hinterlassen, der erklärt, warum
`asyncio.run()` verwendet wird (kein async-Celery-Worker), um Verwirrung bei neuen
Entwicklern zu vermeiden.

**Aufwand:** Minimal. **Priorität:** Niedrig.

---

### 2.4 Frontend-API-Client konsolidieren

**Aktuell:** Jede Ressource hat eine separate API-Datei
(`api/events.ts`, `api/districts.ts`, `api/leaders.ts`, …). Es gibt keine zentrale
Fehlerbehandlung oder Auth-Header-Logik.

**Vereinfachung:** Einen zentralen `httpClient`-Wrapper (Axios-Instanz oder nativer `fetch`
mit Interceptors) einführen, der Auth-Token-Injection und globale Fehlerbehandlung übernimmt.
Die ressourcenspezifischen Dateien bleiben, delegieren aber an den Client.

**Aufwand:** Mittel. **Priorität:** Mittel.

---

### 2.5 Verschlüsselung: SQLAlchemy-Spaltentyp statt manueller Decorator-Logik

**Aktuell:** Credentials werden vor dem Speichern manuell mit `encrypt_credentials()` /
`decrypt_credentials()` aus `application/crypto.py` ver-/entschlüsselt.

**Vereinfachung:** Ein SQLAlchemy `TypeDecorator` (z.B. `EncryptedJSON`) würde
Verschlüsselung/Entschlüsselung transparent beim Laden/Speichern des ORM-Objekts
durchführen – ohne manuelle Aufrufe in jedem Service.

**Aufwand:** Mittel. **Priorität:** Niedrig (aktueller Ansatz ist korrekt und sicher).

---

## 3. Architektonische Lücken

### 3.1 🔴 KRITISCH: PlanningSlot / PlanningSeries fehlt

**Beschreibung:** Das aktuelle `Event`-Modell vermischt Planungs- (Soll), Ausführungs- (Ist)
und Sync-Metadaten. Die Architektur sieht eine Trennung in:

```
PlanningSeries
   └── PlanningSlot (Aggregat-Root)
         ├── EventInstance (Ist-Zustand)
         ├── ServiceAssignments
         └── SyncMetadata
```

**Auswirkung:**
- Keine saubere Trennung zwischen „was geplant war" und „was tatsächlich stattfand"
- Externe Systeme können Planungsdaten unkontrolliert überschreiben
- Sync-Zustandsmaschine (Phase 4) kann nicht ohne dieses Fundament aktiviert werden

**Nächste Schritte:**
1. Migration gemäß `openspec/changes/planning-slot-hybrid-sync/` planen
2. Feature-Flag `USE_PLANNING_SLOT_MODEL` aktivieren
3. Bestehende `Event`-Daten migrieren
4. Matrix-API anpassen (basiert dann auf `PlanningSlot`)

**Referenz:** `openspec/architecture/phase-1-planning-model-technical-plan.md`  
**Priorität:** 🔴 Kritisch – blockiert Phase 3 und 4 der Roadmap.

---

### 3.2 🔴 KRITISCH: RBAC-Durchsetzung unvollständig

**Beschreibung:** Das RBAC-Modell (`User`, `Membership`, `Role`) ist vorhanden. JWT-Claims
enthalten Memberships. Jedoch fehlen konsistente Authorization-Guards in den
Application-Layer-Services.

**Auswirkung:**
- Einzelne Endpoints erlauben ggf. unberechtigt Schreibzugriff
- Governance-Risiko: Daten können von falschen Rollen mutiert werden

**Maßnahmen:**
- Alle Service-Methoden mit `@require_role(...)` oder equivalent absichern
- Automatisierte Tests für Berechtigungsmatrix hinzufügen
- Matrix: `PLANNER`-Rolle für ServiceAssignment-Mutations prüfen

**Referenz:** `openspec/changes/introduce-rbac-permissions-model/`  
**Priorität:** 🔴 Kritisch.

---

### 3.3 🟠 MITTEL: ExternalEventCandidate & Review-Workflow fehlt

**Beschreibung:** Laut Spezifikation sollen neue externe Events nicht automatisch als
`Event` angelegt werden, sondern zunächst als `ExternalEventCandidate` zur manuellen
Prüfung bereitstehen.

**Aktueller Zustand:** Neue externe Events werden direkt als `Event (source=EXTERNAL, status=DRAFT)` gespeichert.

**Auswirkung:**
- Kein Review-Prozess für externe Ereignisse
- Kein Governance-Filter für unbekannte externe Quellen
- Benachrichtigungssystem (das noch fehlt) kann nicht angebunden werden

**Maßnahmen:**
- `ExternalEventCandidate`-Modell und -Repository einführen
- Sync-Service auf Kandidaten-Erstellung umstellen
- Review-UI in der Frontend-App hinzufügen

**Referenz:** `openspec/changes/planning-slot-hybrid-sync/`  
**Priorität:** 🟠 Mittel (nach Phase 1).

---

### 3.4 🟠 MITTEL: Benachrichtigungssystem fehlt

**Beschreibung:** Governance-relevante Ereignisse (externe Erkennung, Sync-Konflikte,
ausstehende Reviews) sollen als persistente In-App-Benachrichtigungen angezeigt werden.

**Aktueller Zustand:** Kein Benachrichtigungsmodell, keine UI-Komponente.

**Maßnahmen:**
- `Notification`-Modell (district_id, type, payload, read_at) einführen
- Domain-Events (`ExternalEventDetected`, `SyncConflictOccurred`) erzeugen Notifications
- Frontend: Notification-Badge im Header mit Dropdown-Liste

**Priorität:** 🟠 Mittel (nach Phase 1).

---

### 3.5 🟠 MITTEL: Rate-Limiting auf öffentlichen Endpoints fehlt

**Beschreibung:** Der Endpoint `GET /api/v1/export/{token}/calendar.ics` ist öffentlich
zugänglich. Ohne Rate-Limiting ist er anfällig für Missbrauch.

**Maßnahmen:**
- SlowAPI oder ein nginx-basiertes Rate-Limit einführen
- Mindestens: 60 Anfragen/Minute pro IP auf `/api/v1/export/*`
- Ggf. auch auf `POST /api/v1/public/districts/{id}/registrations`

**Referenz:** `openspec/changes/introduce-non-functional-baseline/`  
**Priorität:** 🟠 Mittel.

---

### 3.6 🟡 NIEDRIG: ExternalEventLink fehlt

**Beschreibung:** Der `ExternalEventLink` (Mapping zwischen externem Provider-Event
und internem PlanningSlot) ist spezifiziert, aber noch nicht implementiert.

**Auswirkung:** Hash-Vergleiche werden aktuell direkt am `Event.content_hash`-Feld
durchgeführt. Die geplante Sync-Zustandsmaschine benötigt jedoch ein explizites
Link-Objekt mit Revision-Markierungen.

**Priorität:** 🟡 Niedrig (Phase 3 der Roadmap).

---

### 3.7 🟡 NIEDRIG: Kein Health-Check-Endpoint

**Beschreibung:** Es gibt keinen standardisierten Health-Check-Endpoint (z.B. `GET /health`
oder `GET /api/v1/health`), der DB- und Redis-Verbindungsstatus zurückgibt.

**Maßnahmen:**
- Einfachen `GET /health`-Endpoint hinzufügen, der DB-Ping und Redis-Ping prüft
- In Docker Compose als `healthcheck` referenzieren

**Priorität:** 🟡 Niedrig.

---

## 4. Refactoring für bessere Verständlichkeit

### 4.1 Große View-Komponenten aufteilen

Mehrere Frontend-Views sind sehr lang und erledigen zu viele Aufgaben:

| View | Zeilen | Empfehlung |
|------|-------:|------------|
| `EventListView.vue` | 870 | Aufteilen in `EventFilters.vue`, `EventTable.vue`, `EventFormModal.vue` |
| `CalendarIntegrationsView.vue` | 852 | Aufteilen in `IntegrationCard.vue`, `IntegrationFormModal.vue` |
| `MatrixView.vue` | 440 | Aufteilen in `MatrixFilters.vue`, `MatrixTable.vue`, `AssignmentModal.vue` |

**Vorteile:** Bessere Testbarkeit, Wiederverwendbarkeit, einfachere Code-Reviews.  
**Aufwand:** Mittel pro View. **Priorität:** Mittel.

---

### 4.2 Sync-Service aufteilen

`sync_service.py` übernimmt mehrere Verantwortlichkeiten:
- Provider-Auswahl (Factory)
- Sync-Algorithmus (Diff-Logik)
- Ergebnis-Aggregation

**Empfehlung:** In separate Module aufteilen:

```
application/
  sync/
    connector_factory.py    # _get_connector() + Registry
    sync_algorithm.py       # Hash-Diff-Logik (create/update/cancel)
    sync_service.py         # Orchestrierung (läuft weiterhin run_sync())
```

**Aufwand:** Mittel. **Priorität:** Niedrig (funktioniert korrekt, aber schwerer zu testen).

---

### 4.3 Application-Layer: Typisierte Ergebnis-Objekte

**Aktuell:** Services geben `dict[str, int]` zurück (z.B. `{"created": 2, "updated": 1}`).

**Empfehlung:** Pydantic-Dataclasses oder `@dataclass`-Objekte mit klar benannten Feldern
einführen:

```python
@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    cancelled: int = 0
    errors: list[str] = field(default_factory=list)
```

**Vorteil:** Typprüfung bei Compile-Zeit, bessere IDE-Unterstützung, selbstdokumentierend.  
**Aufwand:** Gering. **Priorität:** Niedrig.

---

### 4.4 API-Router: Konsistentes Dependency-Injection-Muster

**Aktuell:** Einige Router verwenden `Depends(get_session)` direkt, andere erhalten
Sessions über zwischengeschaltete Service-Funktionen ohne klares Muster.

**Empfehlung:** Alle Router sollen Services über `Depends()` injizieren:

```python
async def get_matrix(
    district_id: UUID,
    service: MatrixService = Depends(get_matrix_service),
    current_user: User = Depends(get_current_user),
) -> MatrixResponse:
    ...
```

**Aufwand:** Mittel. **Priorität:** Mittel.

---

### 4.5 Domain-Modell: Enum-Werte explizit dokumentieren

Die Enums (`EventStatus`, `EventSource`, `ServiceAssignmentStatus`, usw.) haben
korrekte Werte, aber keine Docstrings. Da sie für Governance-Entscheidungen
kritisch sind, sollten sie dokumentiert werden.

**Aufwand:** Gering. **Priorität:** Niedrig.

---

## 5. UX-Verbesserungen

### 5.1 🔴 Fehlendes globales Feedback-System (Toast/Notification)

**Problem:** Fehler werden inline angezeigt, Erfolgsmeldungen erscheinen in vielen Fällen gar
nicht. Nutzer erhalten kein konsistentes Feedback nach Aktionen (z.B. „Leader gespeichert",
„Sync gestartet").

**Lösung:** Eine globale Toast-Komponente (z.B. mit einem `useToast()`-Composable und
Pinia-Store) einführen. Alle API-Aktionen lösen Success/Error-Toasts aus.

**Aufwand:** Mittel. **Priorität:** 🔴 Hoch.

---

### 5.2 🔴 Kalender-Integration: Sync-Status nicht sichtbar

**Problem:** In der Kalenderintegrationsansicht ist nicht ersichtlich:
- Wann hat der letzte Sync stattgefunden?
- War der letzte Sync erfolgreich?
- Wie viele Events wurden beim letzten Sync erstellt/aktualisiert?

**Lösung:**
- `last_synced_at` und einen optionalen `last_sync_result`-JSON-Wert am `CalendarIntegration`-
  Objekt anzeigen
- Farbcodierter Status-Badge: Grün (Sync OK), Gelb (Sync veraltet), Rot (Sync fehlgeschlagen)
- Tooltip mit letztem Sync-Ergebnis

**Aufwand:** Mittel. **Priorität:** 🔴 Hoch.

---

### 5.3 🟠 Matrix-Ansicht: Keine Ladeanimation / Skeleton-Screen

**Problem:** Beim Laden der Matrix erscheint nur der Text „Lade…". Bei großen Datensätzen
(viele Gemeinden, langer Zeitraum) ist dies unzureichend.

**Lösung:** Skeleton-Screen für die Matrixtabelle mit animierten Platzhaltern (Tailwind
`animate-pulse`). Zusätzlich einen Fortschrittsindikator in der Filter-Leiste.

**Aufwand:** Gering. **Priorität:** 🟠 Mittel.

---

### 5.4 🟠 Matrix-Ansicht: Horizontaler Scroll nicht erkennbar

**Problem:** Bei vielen Spalten (langer Zeitraum) ist horizontales Scrollen nötig, aber
nicht offensichtlich. Insbesondere auf Touch-Geräten.

**Lösung:**
- Scroll-Schatten (CSS box-shadow) am linken/rechten Rand des Tabellen-Containers
- „sticky" erste Spalte (Gemeinde-Name), damit der Kontext beim Scrollen erhalten bleibt
- Scroll-Indikator-Pfeil am rechten Rand

**Aufwand:** Gering bis Mittel. **Priorität:** 🟠 Mittel.

---

### 5.5 🟠 Keine Bestätigungsdialoge für destruktive Aktionen

**Problem:** Aktionen wie „Integration löschen", „Registrierung ablehnen" oder
„Event stornieren" werden ohne Rückfrage ausgeführt.

**Lösung:** Einfaches Bestätigungsmodal (`ConfirmModal.vue`) mit:
- Beschreibung der Aktion
- Warnung (rot) bei unumkehrbaren Aktionen
- „Bestätigen" / „Abbrechen"-Buttons

**Aufwand:** Gering (einmalig + konsequente Nutzung). **Priorität:** 🟠 Mittel.

---

### 5.6 🟠 Export-Token: Kein „In Zwischenablage kopieren"-Button

**Problem:** Export-Tokens und ICS-URLs werden angezeigt, müssen aber manuell kopiert
werden.

**Lösung:** Copy-to-Clipboard-Button neben jeder URL/Token-Anzeige (Clipboard-API +
kurzfristiger „Kopiert!"-Feedback-Badge).

**Aufwand:** Gering. **Priorität:** 🟠 Mittel.

---

### 5.7 🟡 Fehlende Leer-Zustände (Empty States)

**Problem:** Wenn keine Events, keine Integrationen oder keine Leader vorhanden sind,
erscheinen leere Tabellen ohne erklärenden Text.

**Lösung:** Aussagekräftige „Empty State"-Komponente mit:
- Erklärungstext („Noch keine Kalender-Integration vorhanden")
- Direktem CTA-Button („Integration hinzufügen")

**Aufwand:** Gering. **Priorität:** 🟡 Niedrig.

---

### 5.8 🟡 Matrix: Kein Filter nach Gemeinde

**Problem:** Bei Bezirken mit vielen Gemeinden ist es nicht möglich, die Matrix auf
eine einzelne Gemeinde zu filtern.

**Lösung:** Multi-Select oder Freitext-Suchfeld in der Filter-Leiste, das die
angezeigten Zeilen der Matrix filtert (clientseitig, kein API-Aufruf nötig).

**Aufwand:** Gering. **Priorität:** 🟡 Niedrig.

---

### 5.9 🟡 Mobile Responsiveness der Matrix

**Problem:** Die Dienstplan-Matrix ist auf Mobilgeräten kaum nutzbar (zu breite Tabelle,
kleine Touch-Ziele).

**Lösung (kurzfristig):** Deutlicher Hinweis in der UI, dass die Matrix für Desktop
optimiert ist.  
**Lösung (mittelfristig):** Alternative Monats-/Listenansicht für Mobilgeräte einführen.

**Aufwand:** Gering (Hinweis) / Hoch (Alternativansicht). **Priorität:** 🟡 Niedrig.

---

### 5.10 🟡 Registrierungsprozess: Kein E-Mail-Bestätigungsfeedback

**Problem:** Nach der Registrierung als Leader erhält der Nutzer keine Rückmeldung,
dass eine Bestätigungs-E-Mail gesendet wurde (falls diese Funktion geplant ist) oder
dass die Anfrage eingegangen ist.

**Lösung:** Bestätigungsseite / Erfolgsmeldung nach erfolgreicher Registrierung mit
klarer Instruktion: „Ihre Anfrage wurde eingereicht. Der Bezirksadmin wird benachrichtigt."

**Aufwand:** Gering. **Priorität:** 🟡 Niedrig.

---

## 6. Priorisierte Umsetzungsreihenfolge

### Sofort (nächster Sprint)

| # | Maßnahme | Aufwand | Bereich |
|---|----------|---------|---------|
| 1 | RBAC-Guards in allen Services vervollständigen | Mittel | Backend |
| 2 | Globales Toast/Feedback-System | Mittel | Frontend |
| 3 | Kalender-Integration: Sync-Status anzeigen | Mittel | Frontend/Backend |
| 4 | Bestätigungsdialoge für destruktive Aktionen | Gering | Frontend |

### Kurzfristig (Phase 1 – 1–2 Wochen)

| # | Maßnahme | Aufwand | Bereich |
|---|----------|---------|---------|
| 5 | PlanningSlot + PlanningSeries einführen (Feature-Flag) | Hoch | Backend |
| 6 | EventInstance & Soll/Ist-Trennung | Hoch | Backend |
| 7 | ExternalEventCandidate + Review-Workflow | Mittel | Backend/Frontend |
| 8 | Benachrichtigungssystem (Modell + UI-Basis) | Mittel | Backend/Frontend |

### Mittelfristig (Phasen 2–3)

| # | Maßnahme | Aufwand | Bereich |
|---|----------|---------|---------|
| 9 | Große View-Komponenten aufteilen | Mittel | Frontend |
| 10 | ExternalEventLink-Modell + Sync-Metadata | Mittel | Backend |
| 11 | Rate-Limiting auf öffentlichen Endpoints | Gering | Backend/Infra |
| 12 | Copy-to-Clipboard für Export-Tokens | Gering | Frontend |
| 13 | Matrix: sticky Spalte + Scroll-Schatten | Gering | Frontend |

### Langfristig (Phase 4–5)

| # | Maßnahme | Aufwand | Bereich |
|---|----------|---------|---------|
| 14 | Hardened Sync Engine aktivieren | Hoch | Backend |
| 15 | Vollständiges Audit-Logging | Mittel | Backend |
| 16 | Performance-Monitoring & SLOs | Mittel | Backend/Infra |
| 17 | Matrix: Mobile Alternativansicht | Hoch | Frontend |
| 18 | Google/Microsoft OAuth-Flows vollständig | Hoch | Backend |

---

## 7. Verwandte Dokumente

- [OpenSpec Architecture Overview](../openspec/architecture/overview.md)
- [Implementation Roadmap](../openspec/architecture/implementation-roadmap.md)
- [Use Cases](./use-cases.md)
- [Rollenkonzept](./roles.md)
- OpenSpec Change: [`planning-slot-hybrid-sync`](../openspec/changes/planning-slot-hybrid-sync/proposal.md)
- OpenSpec Change: [`introduce-rbac-permissions-model`](../openspec/changes/introduce-rbac-permissions-model/proposal.md)
- OpenSpec Change: [`harden-calendar-sync-algorithm`](../openspec/changes/harden-calendar-sync-algorithm/proposal.md)
- OpenSpec Change: [`introduce-non-functional-baseline`](../openspec/changes/introduce-non-functional-baseline/proposal.md)
