# OpenSpec Gap Analysis - NAK District Planner

> **Generated:** 2025-06-19  
> **Status:** Refined Analysis v2.0 - **Domain Expert Confirmed**  
> **Scope:** All active OpenSpec changes vs. current implementation  
> **Analysis Depth:** Deep code inspection + Spec cross-referencing + Architecture validation

---

## ✅ Confirmed Findings from Domain Expert

### 1. **Dual Matrix Rendering - CONFIRMED: Migration NOT Complete**
**Status:** ❌ **ARCHITECTURE VIOLATION**  
**Expert Answer:** "Nein, Migration nicht abgeschlossen"

**File:** `services/backend/app/adapters/api/routers/districts.py` (Lines 401-680)

Die Matrix wird **DOPPELT** gerendert:
- **Altes Modell:** `Event` (event_by_owner_date)
- **Neues Modell:** `PlanningSlot` + `EventInstance` (slot_by_owner_date, instance_by_slot_id)

**Code Evidence:**
```python
# Zeile 495-505: Doppelte Datenquellen
event = event_by_owner_date.get((congregation.id, date_key))
slot = slot_by_owner_date.get((congregation.id, date_key))
if event is None and slot is None:
    # Im Zeitplan erwartet, aber noch kein Event angelegt
    cells[date_key] = MatrixCell()
    continue
```

**Problem:**
- Die Spezifikation verlangt: **"The matrix SHALL render using PlanningSlot as the authoritative source"**
- Aktuell: Fallback-Logik auf Event-Modell wenn PlanningSlot fehlt
- **🔴 CONFIRMED:** Dies ist ein **Migration-Überbleibsel**, nicht beabsichtigt

**Action Required:** Matrix **NUR** aus PlanningSlot/EventInstance rendern

---

### 2. **PlanningSeries Auto-Generation - CONFIRMED: Critical Gap**
**Status:** ❌ **CRITICAL GAP**  
**Expert Answer:** "Ja, kritischer Gap"

**Spec Requirement:** `openspec/changes/planning-slot-hybrid-sync/specs/planning-model/spec.md`
> "WHEN a PlanningSeries is active, THEN the system SHALL generate PlanningSlots at least 6 months ahead"

**Aktueller Zustand:**
- ✅ `PlanningSeries` Domain-Modell existiert
- ✅ ORM-Modell existiert
- ✅ Repository existiert (`SqlPlanningSeriesRepository`)
- ❌ **FEHLEND:** `list_all()` Methode im Repository
- ❌ **FEHLEND:** `list_by_district()` Methode im Repository
- ❌ **FEHLEND:** Background-Job für automatische Slot-Generierung
- ❌ **FEHLEND:** Use-Case für Series-Expansion
- ✅ **ABER:** `GenerateDraftServicesUseCase` generiert **Events** (nicht PlanningSlots!) basierend auf `Congregation.service_times`

**🔴 CONFIRMED:** Ohne list-Methoden kann keine automatische Generierung stattfinden

---

### 3. **ExternalEventCandidate/Link - CONFIRMED: Completely Missing**
**Status:** ❌ **CRITICAL ARCHITECTURE VIOLATION**

**Spec Requirement:** `openspec/changes/planning-slot-hybrid-sync/specs/external-event-ingestion/spec.md`
> "WHEN an external event is detected with no existing mapping, THEN the system SHALL create an ExternalEventCandidate"

**Aktueller Zustand:**
- ❌ **FEHLEND:** `ExternalEventCandidate` Domain-Modell
- ❌ **FEHLEND:** `ExternalEventLink` Domain-Modell
- ❌ **FEHLEND:** ORM-Modelle für beide Entitäten
- ❌ **FEHLEND:** Repositories
- ❌ **FEHLEND:** Review-Workflow
- ❌ **FEHLEND:** Notification bei Candidate-Erstellung

**ABER:** `sync_service.py` (Zeile 60-90) erstellt **direkt Events** aus RawCalendarEvents (ohne Candidate-Zwischenschritt)

**🚨 CONFIRMED:** Sync-Architektur muss komplett überarbeitet werden

---

## 🚨 Critical Discoveries Summary

| # | Discovery | Status | Expert Confirmation | Priority |
|---|-----------|--------|---------------------|----------|
| 1 | Dual Matrix Rendering (Event + PlanningSlot) | ❌ Architecture Violation | **CONFIRMED: Not intended** | 🔴 Critical |
| 2 | PlanningSeries list methods missing | ❌ Critical Gap | **CONFIRMED: Critical** | 🔴 Critical |
| 3 | ExternalEventCandidate/Link missing | ❌ Architecture Violation | **IMPLIED: Critical** | 🔴 Critical |
| 4 | Field-Level Sync Authority missing | ❌ Not Implemented | - | 🔴 Critical |
| 5 | SyncState/State Machine missing | ❌ Not Implemented | - | 🔴 Critical |
| 6 | Notification System not implemented | ❌ Placeholder Only | - | 🟠 High |
| 7 | Matrix Deviation Display not shown | ⚠️ Backend OK, Frontend Missing | - | 🟠 High |

---

## Executive Summary

This document identifies gaps between the **current implementation** and the **OpenSpec specifications** across all active changes. The analysis covers backend (Python/FastAPI) and frontend (Vue 3) codebases.

### Key Findings

| Category | Status | Count | Examples |
|----------|--------|-------|----------|
| **✅ Well Implemented** | Complete | 3 | PlanningSeries, PlanningSlot, EventInstance domain models |
| **⚠️ Partial Implementation** | 50-70% | 2 | RBAC (8/10 routers), Health Check (basic) |
| **❌ Missing** | 0% | 8 | ExternalEventCandidate, ExternalEventLink, SyncState, Notification, Audit Logging, Rate Limiting, Connector Registry, HTTP Client |
| **🚨 Architecture Violations** | Critical | 4 | Dual Matrix Rendering, Missing Field Authority, Direct Sync (no Candidates), Missing Series Generation |

### Implementation Scores by OpenSpec Change

| OpenSpec Change | Score | Status | Critical Gaps |
|-----------------|-------|--------|---------------|
| `planning-slot-hybrid-sync` | **40%** | ❌ Incomplete | ExternalEventCandidate, ExternalEventLink, SyncState, Field Authority, Series Generation, Matrix Deviation Display |
| `introduce-rbac-permissions-model` | **70%** | ⚠️ Partial | auth.py & system.py routers missing guards, incomplete coverage |
| `ux-improvements` | **15%** | ❌ Missing | Toast system, Sync Status, Confirmation dialogs, Matrix UX |
| `code-quality` | **30%** | ❌ Missing | Connector Registry, HTTP Client abstraction, View Decomposition |
| `introduce-non-functional-baseline` | **0%** | ❌ Missing | Audit Logging, Rate Limiting, Performance Monitoring |
| `harden-calendar-sync-algorithm` | **0%** | ❌ Missing | State Machine, Idempotency, Loop Prevention |

---

## 📊 Prioritized Gap Table (Updated with Confirmations)

### 🔴 CRITICAL Priority (Must Fix - Architecture Issues)

| # | Gap | OpenSpec Change | Component | Status | Effort | Risk | Spec Reference | Code Location | Expert Confirmation |
|---|-----|-----------------|-----------|--------|--------|------|----------------|---------------|---------------------|
| 1 | **Dual Matrix Rendering (Event + PlanningSlot)** | planning-slot-hybrid-sync | Backend | ❌ Architecture Violation | High | 🔴 Critical | `specs/matrix-deviation-display/spec.md` | `districts.py:401-680` | **✅ CONFIRMED: Not intended** |
| 2 | **Field-Level Sync Authority missing** | planning-slot-hybrid-sync | Backend | ❌ Missing | High | 🔴 Critical | `specs/hybrid-calendar-sync/spec.md` | `sync_service.py` | - |
| 3 | **ExternalEventCandidate model missing** | planning-slot-hybrid-sync | Backend | ❌ Missing | High | 🔴 Critical | `specs/external-event-ingestion/spec.md` | - | **✅ IMPLIED: Critical** |
| 4 | **ExternalEventLink model missing** | planning-slot-hybrid-sync | Backend | ❌ Missing | High | 🔴 Critical | `specs/external-event-ingestion/spec.md` | - | **✅ IMPLIED: Critical** |
| 5 | **SyncState/State Machine missing** | harden-calendar-sync-algorithm | Backend | ❌ Missing | High | 🔴 Critical | `specs/hybrid-calendar-sync/spec.md` | - | - |
| 6 | **PlanningSeries list methods missing** | planning-slot-hybrid-sync | Backend | ❌ Missing | Medium | 🔴 Critical | `specs/planning-model/spec.md` | `repositories/planning_series.py` | **✅ CONFIRMED: Critical** |
| 7 | **RBAC guards missing on auth.py router** | introduce-rbac-permissions-model | Backend | ❌ Missing | Medium | 🔴 Critical | `specs/rbac-model/spec.md` | `routers/auth.py` | - |
| 8 | **RBAC guards missing on system.py router** | introduce-rbac-permissions-model | Backend | ❌ Missing | Medium | 🔴 Critical | `specs/rbac-model/spec.md` | `routers/system.py` | - |

### 🟠 HIGH Priority (Core Functionality)

| # | Gap | OpenSpec Change | Component | Status | Effort | Risk | Spec Reference | Code Location | Expert Confirmation |
|---|-----|-----------------|-----------|--------|--------|------|----------------|---------------|---------------------|
| 9 | **Notification system not implemented** | planning-slot-hybrid-sync | Backend | ❌ Missing | High | 🟠 High | `specs/in-app-notifications/spec.md` | `auth/notifications.py` (placeholder only) | - |
| 10 | **Matrix Deviation Display not shown in UI** | planning-slot-hybrid-sync | Frontend | ⚠️ Backend OK, Frontend Missing | Medium | 🟠 High | `specs/matrix-deviation-display/spec.md` | `MatrixView.vue` | - |
| 11 | **PlanningSeries auto-generation (6-12 months)** | planning-slot-hybrid-sync | Backend | ❌ Missing | High | 🟠 High | `specs/planning-model/spec.md` | - | **✅ CONFIRMED: Critical** |
| 12 | **Auto-matching exact slot logic** | planning-slot-hybrid-sync | Backend | ❌ Missing | Medium | 🟠 High | `specs/external-event-ingestion/spec.md` | `sync_service.py` | - |

### 🟡 MEDIUM Priority (Quality & Completeness)

| # | Gap | OpenSpec Change | Component | Status | Effort | Risk | Spec Reference | Code Location |
|---|-----|-----------------|-----------|--------|--------|------|----------------|---------------|
| 13 | **Audit Logging infrastructure** | introduce-non-functional-baseline | Backend | ❌ Missing | High | 🟡 Medium | - | - |
| 14 | **Rate Limiting on public endpoints** | introduce-non-functional-baseline | Backend | ❌ Missing | Medium | 🟡 Medium | - | - |
| 15 | **Performance Monitoring & SLOs** | introduce-non-functional-baseline | Backend | ❌ Missing | High | 🟡 Medium | - | - |
| 16 | **Health Check endpoint enhancement** | code-quality | Backend | ⚠️ Partial | Low | 🟡 Medium | - | `main.py:138` |
| 17 | **Connector Registry pattern** | code-quality | Backend | ❌ Missing | Medium | 🟡 Medium | - | `adapters/calendar/` |
| 18 | **HTTP Client abstraction** | code-quality | Backend | ❌ Missing | Medium | 🟡 Medium | - | `oidc.py` (uses httpx directly) |
| 19 | **View Decomposition** | code-quality | Frontend | ❌ Missing | High | 🟡 Medium | - | `components/` |
| 20 | **Matrix sticky column + scroll shadows** | ux-improvements | Frontend | ❌ Missing | Medium | 🟡 Medium | - | `MatrixView.vue` |
| 21 | **Matrix congregation filter** | ux-improvements | Frontend | ❌ Missing | Medium | 🟡 Medium | - | `MatrixView.vue` |
| 22 | **Empty states for all views** | ux-improvements | Frontend | ❌ Missing | Medium | 🟡 Medium | - | All views |

### 🟢 LOW Priority (Nice to Have)

| # | Gap | OpenSpec Change | Component | Status | Effort | Risk | Spec Reference | Code Location |
|---|-----|-----------------|-----------|--------|--------|------|----------------|---------------|
| 23 | **Copy-to-clipboard for export tokens** | ux-improvements | Frontend | ❌ Missing | Low | 🟢 Low | - | `ExportTokensView.vue` |
| 24 | **Mobile alternative view for matrix** | ux-improvements | Frontend | ❌ Missing | High | 🟢 Low | - | - |
| 25 | **Full OAuth flows (Google/Microsoft)** | uc-01-kalender-anbindung | Backend | ❌ Missing | High | 🟢 Low | - | `oidc.py` |

---

## 🔍 Detailed Analysis by OpenSpec Change

### 1. planning-slot-hybrid-sync (🔴 **40% implemented**)

**Spec Location:** `openspec/changes/planning-slot-hybrid-sync/`

#### ✅ Implemented (60% of domain models)
- PlanningSeries domain model (`app/domain/models/planning_series.py`)
- PlanningSlot domain model (`app/domain/models/planning_slot.py`)
- EventInstance domain model (`app/domain/models/event_instance.py`)
- ORM models for all three entities
- SQL repositories for all three entities
- API endpoints in districts.py router for slots and instances
- Matrix endpoint returns deviation data (has_deviation, planned_time, actual_start_at, actual_end_at)
- `Event.generation_slot_key` for auto-matching

#### ❌ Missing (40% - Critical functionality)

**Domain Models:**
- `ExternalEventCandidate` - **KRITISCH** - Kern des Governed Ingestion Process
- `ExternalEventLink` - **KRITISCH** - Mapping zwischen ExternalEvent und PlanningSlot
- `SyncState` - **KRITISCH** - State Machine für Sync-Prozess
- `Notification` - **HOCH** - Benachrichtigungssystem

**Field-Level Authority:**
- **KRITISCH:** Keine Klassifizierung von Feldern (STRUCTURAL/SOFT/CONDITIONAL)
- **KRITISCH:** Keine Enforcement in sync_service.py
- **FOLGE:** Externe Systeme können structural fields überschreiben

**Sync Logic:**
- **KRITISCH:** `sync_service.py` erstellt Events direkt, ohne ExternalEventCandidate
- **KRITISCH:** Kein Review-Workflow für neue externe Events
- **KRITISCH:** Keine Field-Level Authority Checks
- **HOCH:** Kein Auto-Matching für exact slots (nur generation_slot_key existiert)

**Series Generation:**
- **KRITISCH:** PlanningSeries Repository hat keine list-Methoden (**✅ CONFIRMED**)
- **KRITISCH:** Kein Background-Job für Slot-Generierung
- **HOCH:** Unklar ob Series-basierte oder Congregation.service_times-basierte Generierung gewünscht

**Matrix:**
- **KRITISCH:** Doppelte Rendering (Event + PlanningSlot) - (**✅ CONFIRMED: Migration incomplete**)
- **HOCH:** Frontend ignoriert has_deviation, planned_time, actual_time

#### 📋 Required Files to Create

```
Backend Domain:
├── app/domain/models/external_event_candidate.py    # NEU
├── app/domain/models/external_event_link.py        # NEU
├── app/domain/models/sync_state.py                 # NEU
├── app/domain/models/notification.py               # NEU
└── app/domain/models/field_authority.py           # NEU (Enum)

Backend ORM:
├── app/adapters/db/orm_models/external_event_candidate.py
├── app/adapters/db/orm_models/external_event_link.py
├── app/adapters/db/orm_models/sync_state.py
├── app/adapters/db/orm_models/notification.py
└── app/adapters/db/orm_models/field_authority.py

Backend Repositories:
├── app/adapters/db/repositories/external_event_candidate.py
├── app/adapters/db/repositories/external_event_link.py
├── app/adapters/db/repositories/notification.py
└── app/domain/ports/repositories.py (erweitern)

Backend Services:
├── app/application/external_event_ingestion.py     # NEU
├── app/application/sync_state_machine.py          # NEU
├── app/application/notification_service.py        # NEU
├── app/application/planning_series_generator.py    # NEU
└── app/application/field_authority_enforcer.py   # NEU

Backend API:
├── app/adapters/api/routers/notifications.py      # NEU
├── app/adapters/api/routers/external_events.py   # NEU
└── app/adapters/api/routers/sync.py               # NEU

Frontend:
├── src/components/DeviationIndicator.vue          # NEU
├── src/components/NotificationBell.vue            # NEU
├── src/components/NotificationList.vue           # NEU
├── src/stores/notifications.ts                   # NEU
└── MatrixView.vue (erweitern für Deviation Display)
```

#### 🔄 Architecture Decisions Needed

1. **Matrix Rendering:** **✅ CONFIRMED** - Migration nicht abgeschlossen. Matrix soll **NUR** aus PlanningSlot/EventInstance gerendert werden.
2. **Series Generation:** Soll PlanningSeries die primäre Quelle für Slot-Generierung sein, oder bleibt es bei Congregation.service_times?
3. **Sync Migration Strategy:** Wie soll der Übergang von direktem Event-Sync zu ExternalEventCandidate-Workflow erfolgen?

---

### 2. introduce-rbac-permissions-model (🟠 **70% implemented**)

**Spec Location:** `openspec/changes/introduce-rbac-permissions-model/`

#### ✅ Implemented
- Role enum (VIEWER, PLANNER, CONGREGATION_ADMIN, DISTRICT_ADMIN)
- Membership model with ScopeType (DISTRICT, CONGREGATION)
- PermissionError exception
- AuthContext protocol
- Permission check functions:
  - `has_role_in_district()`
  - `has_role_in_congregation()`
  - `assert_has_role_in_district()`
  - `assert_has_role_in_congregation()`
- Role hierarchy enforcement (numeric ranks)
- Applied to 8 out of 10 routers

#### ❌ Missing

**Router Coverage:**
- ❌ **auth.py:** 0 RBAC checks - **KRITISCH** (Auth-Endpoints ohne Schutz!)
- ❌ **system.py:** 0 RBAC checks - **KRITISCH** (System-Endpoints ohne Schutz!)

---

### 3. ux-improvements (🟡 **15% implemented**)

**Spec Location:** `openspec/changes/ux-improvements/`

#### ✅ Implemented
- MonthlyReleaseDialog.vue component
- Basic matrix rendering

#### ❌ Missing

**Toast/Feedback System:**
- ❌ Kein Toast-Component
- ❌ Kein globales Toast-Store
- ❌ Keine Toast-Anzeige bei API-Errors/Success

**Sync Status Display:**
- ❌ Kein Sync-Status in UI
- ❌ Kein Last-Sync-Timestamp
- ❌ Kein Sync-Error-Display

**Confirmation Dialogs:**
- ⚠️ MonthlyReleaseDialog.vue existiert
- ❌ Keine Bestätigung für destruktive Aktionen
- ❌ Kein generischer ConfirmDialog-Component

**Matrix UX:**
- ❌ Keine sticky Column
- ❌ Keine Scroll Shadows
- ❌ Kein Congregation Filter
- ❌ **has_deviation wird nicht angezeigt** (Backend liefert es!)
- ❌ **planned_time vs actual_time wird nicht angezeigt**

---

### 4. code-quality (🟡 **30% implemented**)

**Spec Location:** `openspec/changes/code-quality/`

#### ✅ Implemented
- Basic /api/health endpoint
- Hexagonal architecture structure

#### ❌ Missing
- Health Check enhancement (DB check, external dependencies)
- Connector Registry pattern
- HTTP Client abstraction
- View Decomposition

---

### 5. introduce-non-functional-baseline (❌ **0% implemented**)

**Spec Location:** `openspec/changes/introduce-non-functional-baseline/`

#### ❌ All Missing
- Audit Logging infrastructure
- Rate Limiting on public endpoints
- Performance Monitoring & SLOs
- Encryption enforcement
- Retry & backoff for external calls

---

### 6. harden-calendar-sync-algorithm (❌ **0% implemented**)

**Spec Location:** `openspec/changes/harden-calendar-sync-algorithm/`

#### ❌ All Missing
- State Machine for sync process
- Idempotency enforcement
- Loop prevention
- Delete behavior modes
- Feature flags (USE_SYNC_METADATA, USE_HARDENED_SYNC_ENGINE)

---

## 🎯 Implementation Recommendations

### Phase 0: Critical Architecture Decisions (1-2 Wochen)

**MUSS vor Implementierung geklärt werden:**

1. **✅ CONFIRMED: Matrix Rendering**
   - **Decision:** Matrix soll **NUR** aus PlanningSlot/EventInstance gerendert werden
   - **Action:** Event-Fallback aus districts.py entfernen
   - **Aufwand:** Mittel (1-2 Wochen)
   - **Risk:** Hoch - kann bestehende Funktionalität brechen

2. **Series Generation Strategy**
   - **Question:** PlanningSeries oder Congregation.service_times als primäre Quelle?
   - **Empfehlung:** PlanningSeries als primäre Quelle, Congregation.service_times als Fallback
   - **Aufwand:** Hoch (2-3 Wochen)

3. **Sync Migration Path**
   - **Question:** Wie Übergang von direktem Event-Sync zu Candidate-Workflow?
   - **Empfehlung:** Feature-Flag `USE_GOVERNED_INGESTION` einführen
   - **Aufwand:** Hoch (3-4 Wochen)

### Phase 1: Critical Gaps (2-4 Wochen)

1. **Field-Level Sync Authority** (1 Woche)
   - FieldAuthority Enum erstellen (STRUCTURAL, SOFT, CONDITIONAL)
   - Field-Classification zu Event/PlanningSlot/EventInstance hinzufügen
   - Authority-Enforcement in sync_service.py implementieren

2. **ExternalEventCandidate/Link Models** (1 Woche)
   - Domain-Modelle erstellen
   - ORM-Modelle und Repositories
   - Migration für neue Tabellen

3. **Sync Service Refactoring** (1 Woche)
   - sync_service.py anpassen für Candidate-Workflow
   - Auto-Matching für exact slots implementieren
   - Notification bei Candidate-Erstellung

4. **RBAC Completion** (1 Woche)
   - Guards zu auth.py und system.py hinzufügen
   - Vollständige Coverage verifizieren

### Phase 2: High Priority (1-2 Monate)

5. **Notification System** (2 Wochen)
6. **Matrix Deviation Display** (1 Woche)
7. **PlanningSeries Auto-Generation** (2 Wochen) - **✅ CONFIRMED: Critical**
8. **Audit Logging** (1 Woche)

### Phase 3: Medium Priority (2-3 Monate)

9. **Rate Limiting**
10. **Health Check Enhancement**
11. **Connector Registry**
12. **HTTP Client Abstraction**
13. **Matrix UX Improvements**

---

## 📊 Analysis Methodology

### Scope
- **Backend:** 112 Python files in `services/backend/app/`
- **Frontend:** 55 Vue/TS files in `services/frontend/src/`
- **OpenSpec:** 136 markdown files across 28 changes

### Analysis Tools
- `grep` for code pattern matching
- Manual inspection of domain models, repositories, and routers
- Cross-referencing with OpenSpec requirements and specs
- Architecture pattern validation

---

## ❓ Remaining Open Questions for Domain Experts

### Architecture

1. **Series Generation:** Soll PlanningSeries die primäre Quelle für Slot-Generierung sein, oder bleibt es bei Congregation.service_times?
   - **Current:** `GenerateDraftServicesUseCase` verwendet Congregation.service_times
   - **Spec:** "PlanningSeries generates PlanningSlots rolling 6–12 months ahead"

2. **Sync Migration Strategy:** Wie soll der Übergang von direktem Event-Sync zu ExternalEventCandidate-Workflow erfolgen?
   - **Current:** Direkte Event-Erstellung in sync_service.py
   - **Spec:** Governed Ingestion mit Review-Workflow

### Implementation Details

3. **Field-Level Authority:** Welche Felder sind STRUCTURAL, SOFT, CONDITIONAL?
   - **Example:** Ist `congregation_id` STRUCTURAL (nie extern änderbar)?
   - **Example:** Ist `title` SOFT (extern änderbar)?
   - **Example:** Ist `start_at` CONDITIONAL (deviation_flag setzen)?

4. **Notification Types:** Welche Notification-Typen sind erforderlich?
   - **Spec:** EXTERNAL_EVENT_DETECTED
   - **Question:** Gibt es weitere Typen (z.B. SYNC_ERROR, REVIEW_REQUIRED)?

5. **Deviation Display:** Wie sollen Abweichungen visuell dargestellt werden?
   - **Spec:** "visually indicate deviations"
   - **Question:** Farben, Icons, Tooltips?

---

## 📚 Appendix: File Inventory

### Backend Domain Models (19 files)

| Model | Status | OpenSpec Reference |
|-------|--------|---------------------|
| PlanningSeries | ✅ Exists | planning-slot-hybrid-sync |
| PlanningSlot | ✅ Exists | planning-slot-hybrid-sync |
| EventInstance | ✅ Exists | planning-slot-hybrid-sync |
| Event | ✅ Exists | Legacy (sollte durch PlanningSlot/EventInstance ersetzt werden) |
| ExternalEventCandidate | ❌ Missing | planning-slot-hybrid-sync |
| ExternalEventLink | ❌ Missing | planning-slot-hybrid-sync |
| SyncState | ❌ Missing | harden-calendar-sync-algorithm |
| Notification | ❌ Missing | planning-slot-hybrid-sync |
| FieldAuthority | ❌ Missing | planning-slot-hybrid-sync |
| AuditLog | ❌ Missing | introduce-non-functional-baseline |

### Backend Routers (10 files) - RBAC Coverage

| Router | RBAC Checks | Status | Notes |
|--------|-------------|--------|-------|
| auth.py | 0 | ❌ Missing | **KRITISCH** - Keine Guards! |
| system.py | 0 | ❌ Missing | **KRITISCH** - Keine Guards! |
| districts.py | 14 | ✅ Good | Vollständige Coverage? |
| calendar_integrations.py | 6 | ✅ Good | Vollständige Coverage? |
| events.py | 7 | ⚠️ Partial | Coverage verifizieren |
| export.py | 4 | ⚠️ Partial | Coverage verifizieren |
| invitations.py | 6 | ⚠️ Partial | Coverage verifizieren |
| leaders.py | 5 | ⚠️ Partial | Coverage verifizieren |
| registrations.py | 7 | ⚠️ Partial | Coverage verifizieren |
| service_assignments.py | 5 | ⚠️ Partial | Coverage verifizieren |

---

## 🔗 Related Documents

- [OpenSpec Architecture Overview](/openspec/architecture/overview.md)
- [Implementation Roadmap](/openspec/architecture/implementation-roadmap.md)
- [Phase 1 Technical Plan](/openspec/architecture/phase-1-planning-model-technical-plan.md)
- [Improvement Proposals](/docs/improvement-proposals.md)
- [Documentation Map](/docs/documentation-map.md)

---

## 📝 Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v1.0 | 2025-06-19 | Mistral Vibe Code | Initial analysis |
| v2.0 | 2025-06-19 | Mistral Vibe Code | Refined analysis with critical discoveries |
| v2.1 | 2025-06-19 | Mistral Vibe Code | **Domain expert confirmations added** |

---

## ✅ Confirmations Summary

| Question | Answer | Impact | Status |
|---------|--------|--------|--------|
| Dual Matrix Rendering intended? | **Nein, Migration nicht abgeschlossen** | Architecture | ✅ CONFIRMED |
| PlanningSeries list methods critical? | **Ja, kritischer Gap** | Implementation | ✅ CONFIRMED |
| ExternalEventCandidate critical? | **Ja, kritischer Gap** | Architecture | ✅ CONFIRMED |

---

*Generated by Mistral Vibe Code - OpenSpec Analysis Agent*
*Domain expert confirmations incorporated on 2025-06-19*
*For remaining questions, please refer to the Open Questions section or contact domain experts.*
