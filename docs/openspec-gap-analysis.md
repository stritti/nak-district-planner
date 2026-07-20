# OpenSpec Gap Analysis - NAK District Planner

> **Generated:** 2026-06-19  
> **Status:** ⚠️ HISTORISCH — Siehe `docs/code-review-2026-07.md` für aktuelle Analyse  
> **Scope:** All active OpenSpec changes vs. current implementation  
>
> **Hinweis:** Dieses Dokument ist in wesentlichen Punkten veraltet. Aussagen zu "0 RBAC-Checks in
> auth.py/system.py", "kein Rate-Limiting", "kein Audit-Logging" und "kein Toast-System"
> sind überholt — diese Komponenten existieren inzwischen. Für den aktuellen Stand siehe
> `docs/code-review-2026-07.md` und `docs/code-review-2026-07-action-plan.md`.

---

## Executive Summary

This document identifies gaps between the **current implementation** and the **OpenSpec specifications** across all active changes. The analysis covers backend (Python/FastAPI) and frontend (Vue 3) codebases.

### Key Findings

- **✅ Well Implemented:** Planning model (PlanningSeries, PlanningSlot, EventInstance) exists in domain layer
- **⚠️ Partial Implementation:** RBAC permissions exist but are not applied to all endpoints
- **❌ Missing:** ExternalEventCandidate, ExternalEventLink, SyncState, Audit Logging, Rate Limiting
- **❌ Missing:** Frontend Toast system, Sync Status display, Confirmation dialogs
- **❌ Missing:** Non-functional baseline (Rate Limiting, Audit Logging, Performance SLOs)

---

## Prioritized Gap Table

| # | Gap | OpenSpec Change | Component | Status | Priority | Effort | Risk | Notes |
|---|-----|-----------------|-----------|--------|----------|--------|------|-------|
| 1 | RBAC guard gaps in events.py and remaining routers | introduce-rbac-permissions-model | Backend | ⚠️ Partial | 🟡 Medium | Medium | Medium | system.py already requires CurrentUserWithMemberships + admin/superadmin; auth.py has intentionally public OIDC endpoints and authenticated /me/access. Remaining routers lack systematic checks |
| 2 | RBAC guards incomplete on events.py router | introduce-rbac-permissions-model | Backend | ⚠️ Partial | 🔴 Critical | Medium | Medium | Only 7 checks found, likely incomplete |
| 3 | ExternalEventCandidate model not implemented | planning-slot-hybrid-sync | Backend | ❌ Missing | 🔴 Critical | High | High | Required for candidate review workflow |
| 4 | ExternalEventLink model not implemented | planning-slot-hybrid-sync | Backend | ❌ Missing | 🔴 Critical | High | High | Required for sync metadata tracking |
| 5 | SyncState/state machine not implemented | harden-calendar-sync-algorithm | Backend | ❌ Missing | 🔴 Critical | High | High | Core sync stabilization feature |
| 6 | PlanningSlot series generation (6 months ahead) | planning-slot-hybrid-sync | Backend | ⚠️ Partial | 🟠 High | Medium | Medium | Model exists but auto-generation unclear |
| 7 | Matrix deviation display not implemented | planning-slot-hybrid-sync | Frontend | ❌ Missing | 🟠 High | High | Medium | Visual deviation indicators missing |
| 8 | Global Toast/Feedback system | ux-improvements | Frontend | ❌ Missing | 🟠 High | Medium | Low | No toast component found |
| 9 | Sync Status display | ux-improvements | Frontend | ❌ Missing | 🟠 High | Medium | Low | User needs visibility into sync state |
| 10 | Confirmation dialogs for destructive actions | ux-improvements | Frontend | ⚠️ Partial | 🟠 High | Medium | Low | Some dialogs exist (MonthlyReleaseDialog) |
| 11 | Audit Logging infrastructure | introduce-non-functional-baseline | Backend | ❌ Missing | 🟡 Medium | High | Medium | Required for compliance and debugging |
| 12 | Rate Limiting on public endpoints | introduce-non-functional-baseline | Backend | ❌ Missing | 🟡 Medium | Medium | Low | Security best practice |
| 13 | Performance Monitoring & SLOs | introduce-non-functional-baseline | Backend | ❌ Missing | 🟡 Medium | High | Low | Observability requirement |
| 14 | Health Check endpoint enhancement | code-quality | Backend | ⚠️ Partial | 🟡 Medium | Low | Low | Basic /api/health exists, needs depth |
| 15 | Connector Registry pattern | code-quality | Backend | ❌ Missing | 🟡 Medium | Medium | Low | For external calendar adapters |
| 16 | HTTP Client abstraction | code-quality | Backend | ❌ Missing | 🟡 Medium | Medium | Low | Currently using httpx directly |
| 17 | View Decomposition | code-quality | Frontend | ❌ Missing | 🟡 Medium | High | Low | Component organization improvement |
| 18 | In-App Notifications model | planning-slot-hybrid-sync | Backend | ❌ Missing | 🟡 Medium | High | Medium | Notification system foundation |
| 19 | Matrix sticky column + scroll shadows | ux-improvements | Frontend | ❌ Missing | 🟡 Medium | Medium | Low | UX enhancement |
| 20 | Matrix congregation filter | ux-improvements | Frontend | ❌ Missing | 🟡 Medium | Medium | Low | UX enhancement |
| 21 | Empty states for all views | ux-improvements | Frontend | ❌ Missing | 🟡 Medium | Medium | Low | UX polish |
| 22 | Copy-to-clipboard for export tokens | ux-improvements | Frontend | ❌ Missing | 🟡 Medium | Low | Low | Quality of life |
| 23 | Mobile alternative view for matrix | ux-improvements | Frontend | ❌ Missing | 🟢 Low | High | Low | Future enhancement |
| 24 | Full OAuth flows (Google/Microsoft) | uc-01-kalender-anbindung | Backend | ❌ Missing | 🟢 Low | High | Medium | Phase 4 feature |

---

## Detailed Analysis by OpenSpec Change

### 1. planning-slot-hybrid-sync (🔴 Critical)

**Status:** Partially Implemented  
**Implementation Score:** 60%

#### ✅ Implemented
- PlanningSeries domain model (`app/domain/models/planning_series.py`)
- PlanningSlot domain model (`app/domain/models/planning_slot.py`)
- EventInstance domain model (`app/domain/models/event_instance.py`)
- ORM models for all three entities
- SQL repositories for all three entities
- API endpoints in districts.py router for slots and instances

#### ❌ Missing
- **ExternalEventCandidate** model and repository
- **ExternalEventLink** model and repository
- **SyncState** enumeration and state machine logic
- Auto-generation of PlanningSlots 6 months ahead
- Matrix rendering based on PlanningSlot as authoritative source
- Deviation indicators in matrix view
- Candidate review workflow
- Sync metadata persistence (hashes, revision markers)

#### 📋 Files to Create/Modify
- `app/domain/models/external_event_candidate.py`
- `app/domain/models/external_event_link.py`
- `app/domain/models/sync_state.py`
- `app/adapters/db/orm_models/external_event_candidate.py`
- `app/adapters/db/orm_models/external_event_link.py`
- `app/adapters/db/repositories/external_event_candidate.py`
- `app/adapters/db/repositories/external_event_link.py`
- Frontend matrix component updates
- Sync state machine service

---

### 2. introduce-rbac-permissions-model (🔴 Critical)

**Status:** Partially Implemented  
**Implementation Score:** 70%

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
- Role hierarchy enforcement
- Applied to 8 out of 10 routers

#### ❌ Missing
- **auth.py router:** No RBAC guards found
- **system.py router:** No RBAC guards found
- **Complete coverage:** Need to verify all endpoints in other routers
- **JWT claims validation:** Need to verify role claims are properly extracted

#### ⚠️ Concerns
- 54 permission checks found across 8 routers, but distribution is uneven
- Some routers may have incomplete coverage
- No centralized audit of which endpoints are protected

#### 📋 Files to Review/Modify
- `app/adapters/api/routers/auth.py` - Add RBAC guards
- `app/adapters/api/routers/system.py` - Add RBAC guards
- Audit all routers for complete endpoint coverage
- Create permission coverage test

---

### 3. ux-improvements (🟠 High)

**Status:** Minimally Implemented  
**Implementation Score:** 20%

#### ✅ Implemented
- MonthlyReleaseDialog.vue component exists
- Some confirmation patterns may exist

#### ❌ Missing
- **Global Toast/Feedback system** - No toast component found
- **Sync Status display** - No sync status UI found
- **Confirmation dialogs** - Only MonthlyReleaseDialog found, need for all destructive actions
- **Matrix UX improvements:**
  - Sticky column
  - Scroll shadows
  - Congregation filter
- **Empty states** - No empty state components found
- **Copy-to-clipboard** - Not implemented for export tokens
- **Mobile matrix view** - Not implemented

#### 📋 Files to Create/Modify
- `components/Toast.vue` or use library (Sonner, Vue Toastification)
- `components/ConfirmDialog.vue`
- `components/EmptyState.vue`
- Matrix view enhancements
- Export token display with copy functionality

---

### 4. code-quality (🟡 Medium)

**Status:** Minimally Implemented  
**Implementation Score:** 30%

#### ✅ Implemented
- Basic /api/health endpoint exists
- Hexagonal architecture structure (adapters, application, domain)

#### ❌ Missing
- **Health Check enhancement** - Basic endpoint exists but lacks depth (DB check, external dependencies)
- **Connector Registry** - External calendar adapters not using registry pattern
- **HTTP Client abstraction** - Using httpx directly in OIDC adapter
- **View Decomposition** - Frontend components could be better organized

#### 📋 Files to Create/Modify
- Enhanced health check with dependency checks
- Connector registry abstraction
- HTTP client wrapper/abstraction
- Frontend component reorganization

---

### 5. introduce-non-functional-baseline (🟡 Medium)

**Status:** Not Implemented  
**Implementation Score:** 0%

#### ❌ Missing
- **Audit Logging** - No audit log infrastructure found
- **Rate Limiting** - No rate limiting on any endpoints
- **Performance Monitoring** - No SLO tracking or monitoring
- **Encryption enforcement** - Not verified in codebase
- **Retry & backoff** - Not implemented for external calls

#### 📋 Files to Create/Modify
- Audit logging middleware/service
- Rate limiting configuration (FastAPI middleware)
- Performance monitoring setup (Prometheus, OpenTelemetry)
- Retry logic for external API calls

---

### 6. harden-calendar-sync-algorithm (🟡 Medium)

**Status:** Not Implemented  
**Implementation Score:** 0%

#### ❌ Missing
- **State machine** for sync process
- **Idempotency enforcement**
- **Loop prevention**
- **Delete behavior modes**
- **Feature flags:** USE_SYNC_METADATA, USE_HARDENED_SYNC_ENGINE

#### 📋 Files to Create/Modify
- Sync state machine implementation
- Idempotency keys and checks
- Loop detection logic
- Configurable delete behavior
- Feature flag infrastructure

---

## Implementation Recommendations

### Phase 1: Critical Gaps (Next 2-4 Weeks)
1. **Complete RBAC implementation** - Add guards to all routers
2. **Implement ExternalEventCandidate** - Foundation for sync workflow
3. **Implement ExternalEventLink** - Sync metadata tracking
4. **Basic SyncState** - Minimal state tracking

### Phase 2: High Priority (Next 1-2 Months)
5. **Toast system** - User feedback foundation
6. **Sync Status display** - Visibility for users
7. **Confirmation dialogs** - Safety for destructive actions
8. **Audit Logging** - Compliance and debugging

### Phase 3: Medium Priority (Next 2-3 Months)
9. **Rate Limiting** - Security hardening
10. **Health Check enhancement** - Better observability
11. **Connector Registry** - Better adapter management
12. **Matrix UX improvements** - User experience

### Phase 4: Nice to Have (Future)
13. **Performance Monitoring** - Full observability
14. **View Decomposition** - Code quality
15. **Mobile matrix view** - Accessibility
16. **Full OAuth flows** - Integration completeness

---

## Analysis Methodology

### Scope
- **Backend:** 112 Python files in `services/backend/app/`
- **Frontend:** 55 Vue/TS files in `services/frontend/src/`
- **OpenSpec:** 136 markdown files across 28 changes

### Tools Used
- `grep` for code pattern matching
- Manual inspection of domain models and routers
- Cross-referencing with OpenSpec requirements

### Limitations
- This is a static code analysis, not a runtime verification
- Some features may exist but not be discoverable via simple grep
- Test coverage not analyzed
- Frontend component usage not fully traced

---

## Next Steps

1. **Review and validate** this analysis with domain experts
2. **Prioritize** gaps based on business needs
3. **Create implementation tasks** for each gap
4. **Track progress** against OpenSpec specifications
5. **Update** this document as gaps are closed

---

## Appendix: File Inventory

### Backend Domain Models (19 files)
- ✅ PlanningSeries, PlanningSlot, EventInstance
- ❌ ExternalEventCandidate, ExternalEventLink, SyncState
- ❌ AuditLog, RateLimitConfig

### Backend Routers (10 files)
- ✅ districts.py (14 RBAC checks)
- ✅ calendar_integrations.py (6 RBAC checks)
- ✅ events.py (7 RBAC checks)
- ✅ export.py (4 RBAC checks)
- ✅ invitations.py (6 RBAC checks)
- ✅ leaders.py (5 RBAC checks)
- ✅ registrations.py (7 RBAC checks)
- ✅ service_assignments.py (5 RBAC checks)
- ❌ auth.py (0 RBAC checks)
- ❌ system.py (0 RBAC checks)

### Frontend Components (6 files)
- ✅ MonthlyReleaseDialog.vue
- ❌ Toast.vue, ConfirmDialog.vue, EmptyState.vue
- ❌ Matrix enhancements

---

*Generated by Mistral Vibe Code - OpenSpec Analysis Agent*
