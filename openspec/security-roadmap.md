# Security Roadmap - NAK District Planner

**Version:** 1.0.0  
**Datum:** 2025-06-19  
**Status:** Aktiv  
**Verantwortlich:** Security Team  

---

## 🎯 Übersicht

Diese Roadmap definiert die **priorisierten Sicherheitsmassnahmen** basierend auf der [Security Analyse](docs/security-analysis.md). Sie enthält detaillierte OpenSpec Spezifikationen für die Umsetzung der wichtigsten Sicherheitsfeatures.

### 📊 Priorisierungsmatrix

| Priorität | Risikostufe | Zeitrahmen | Team |
|-----------|--------------|------------|------|
| **HIGH** (Sofort) | Kritisch/Hoch | Q3 2025 | Backend |
| **MEDIUM** (Mittelfristig) | Hoch/Mittel | Q4 2025 | Backend |
| **LOW** (Langfristig) | Mittel/Niedrig | 2026 | Security |

---

## 🚨 HIGH Priority (Q3 2025) - Sofortmassnahmen

### 1. **Audit-Logging implementieren** (SEC-009)

**Status:** ❌ Nicht implementiert  
**Risiko:** Hoch (OWASP A09, CIS 8.1)  
**Aufwand:** ~4 Wochen  
**OpenSpec:** [`implement-audit-logging`](changes/implement-audit-logging/)  

#### 📋 Spezifikation

| Dokument | Beschreibung | Status |
|----------|-------------|--------|
| [proposal.md](changes/implement-audit-logging/proposal.md) | Warum, Was, Fähigkeiten | ✅ Fertig |
| [design.md](changes/implement-audit-logging/design.md) | Detaillierte Implementierung | ✅ Fertig |
| [tasks.md](changes/implement-audit-logging/tasks.md) | Aufgabenliste | ⏳ Geplant |

#### 🎯 Ziele
- Alle schreibenden Operationen auditierbar machen
- Unveränderliche Audit-Logs erstellen
- Compliance mit OWASP A09 und CIS 8.1
- Performance-Impact < 5%

#### 📦 Komponenten
- `audit_logs` Tabelle in PostgreSQL
- `AuditLoggingService` für Log-Erstellung
- `AuditMiddleware` für automatisches Request-Logging
- `@audit_action` Decorator für manuelles Logging
- `AuditAPI` für Log-Abfragen (Superadmin)
- `AuditRetentionService` für Log-Bereinigung

#### 🔗 Abhängigkeiten
- PostgreSQL
- Redis (optional für asynchrones Logging)

---

### 2. **Rate Limiting implementieren** (SEC-016)

**Status:** ❌ Nicht implementiert  
**Risiko:** Hoch (OWASP A05, CIS 4.1)  
**Aufwand:** ~2 Wochen  
**OpenSpec:** [`implement-rate-limiting`](changes/implement-rate-limiting/)  

#### 📋 Spezifikation

| Dokument | Beschreibung | Status |
|----------|-------------|--------|
| [proposal.md](changes/implement-rate-limiting/proposal.md) | Warum, Was, Fähigkeiten | ✅ Fertig |
| [design.md](changes/implement-rate-limiting/design.md) | Detaillierte Implementierung | ✅ Fertig |
| [tasks.md](changes/implement-rate-limiting/tasks.md) | Aufgabenliste | ⏳ Geplant |

#### 🎯 Ziele
- Alle öffentlichen Endpunkte vor DoS schützen
- Standardisierte Rate-Limit Header
- Konfigurierbare Limits pro Endpunkt
- Performance-Impact < 1ms

#### 📦 Komponenten
- `RateLimiter` Klasse (Redis-basiert, Sliding Window)
- `RateLimitMiddleware` für FastAPI
- `RateLimitConfig` für Konfiguration
- `BurstRateLimiter` für Burst Protection
- `RateLimitMetrics` für Monitoring

#### 🔗 Abhängigkeiten
- Redis (bereits vorhanden)

#### 📊 Konfiguration
```yaml
# Default Limits
RATE_LIMIT_DEFAULT_LIMIT: 200
RATE_LIMIT_DEFAULT_WINDOW: 60

# Endpunkt-spezifisch
RATE_LIMIT_ENDPOINTS:
  "/api/v1/export/*/calendar.ics": {limit: 60, window: 60}
  "/api/v1/auth/oidc/discovery": {limit: 100, window: 60}
  "/api/v1/auth/oidc/token": {limit: 100, window: 60}
```yaml

---

### 3. **CSRF-Schutz implementieren** (SEC-004)

**Status:** ❌ Nicht implementiert  
**Risiko:** Hoch (OWASP A01)  
**Aufwand:** ~2 Wochen  
**OpenSpec:** [`implement-csrf-protection`](changes/implement-csrf-protection/)  

#### 📋 Spezifikation

| Dokument | Beschreibung | Status |
|----------|-------------|--------|
| [proposal.md](changes/implement-csrf-protection/proposal.md) | Warum, Was, Fähigkeiten | ✅ Fertig |
| [design.md](changes/implement-csrf-protection/design.md) | Detaillierte Implementierung | ✅ Fertig |
| [tasks.md](changes/implement-csrf-protection/tasks.md) | Aufgabenliste | ⏳ Geplant |

#### 🎯 Ziele
- Alle state-changing Requests vor CSRF schützen
- Kryptografisch sichere Tokens (HMAC-SHA256)
- Kompatibilität mit OIDC Flow
- Performance-Impact < 0.5ms

#### 📦 Komponenten
- `CSRFTokenService` für Token-Management
- `CSRFMiddleware` für FastAPI
- Frontend Integration (`useCSRF` Composable)
- Ausnahmen für API-Key Auth

#### 🔗 Abhängigkeiten
- Keine neuen Abhängigkeiten

#### 🎨 Frontend Änderungen
- `useCSRF()` Composable
- Axios Interceptors für CSRF-Headers
- Automatische Token-Rotation

---

### 4. **Tenant-Isolation verbessern** (SEC-020, SEC-021)

**Status:** ⚠️ Teilweise implementiert  
**Risiko:** Kritisch (OWASP A01)  
**Aufwand:** ~5 Wochen  
**OpenSpec:** [`improve-tenant-isolation`](changes/improve-tenant-isolation/)  

#### 📋 Spezifikation

| Dokument | Beschreibung | Status |
|----------|-------------|--------|
| [proposal.md](changes/improve-tenant-isolation/proposal.md) | Warum, Was, Fähigkeiten | ✅ Fertig |
| [design.md](changes/improve-tenant-isolation/design.md) | Detaillierte Implementierung | ✅ Fertig |
| [tasks.md](changes/improve-tenant-isolation/tasks.md) | Aufgabenliste | ✅ Fertig |

#### 🎯 Ziele
- Vollständige Tenant-Isolation auf Application- und DB-Ebene
- Verhindern von Cross-Tenant Data Access
- Defense in Depth durch mehrere Schichten
- Performance-Impact < 2%

#### 📦 Komponenten
- `TenantContext` für Kontextvariable
- `TenantMiddleware` für Request-Extraktion
- PostgreSQL RLS Policies für alle Tenant-Tabellen
- `TenantAwareRepository` Basis-Klasse
- `TenantValidationService` für explizite Validierung
- `@validate_tenant_district` Decorator
- `@validate_tenant_congregation` Decorator

#### 🔗 Abhängigkeiten
- PostgreSQL (RLS Support)

#### 🏗️ Multi-Layer Architektur
```ascii
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Tenant Middleware → Tenant Context → Permission Checks          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  TenantValidationService → TenantAwareRepository                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL RLS Policies → Tenant-specific Queries               │
└─────────────────────────────────────────────────────────────────┘
```ascii

---

## 📅 MEDIUM Priority (Q4 2025) - Mittelfristige Massnahmen

### 5. **API-Key Rotation** (SEC-002)

**Status:** ⚠️ Teilweise implementiert  
**Risiko:** Hoch  
**Aufwand:** ~2 Wochen  

#### 🎯 Ziele
- Automatisierte Rotation von API-Keys
- Grace Period für alte Keys
- Audit-Logging für Key-Operationen

#### 📦 Komponenten
- `APIKeyManager` mit Rotation
- `APIKeyRepository` mit Expiry-Check
- Celery Task für regelmäßige Rotation
- API-Endpunkte für Key-Management

---

### 6. **Security Headers** (A05)

**Status:** ❌ Nicht implementiert  
**Risiko:** Mittel  
**Aufwand:** ~1 Woche  

#### 🎯 Ziele
- CSP, HSTS, X-Frame-Options Header
- X-Content-Type-Options, X-XSS-Protection
- Permissions-Policy

#### 📦 Komponenten
- `SecurityHeadersMiddleware`
- Konfiguration pro Environment

---

### 7. **DSGVO Compliance** (GDPR)

**Status:** ❌ Nicht implementiert  
**Risiko:** Mittel  
**Aufwand:** ~3 Wochen  

#### 🎯 Ziele
- Löschkonzept implementieren
- Betroffenenrechte umsetzen (Export, Löschung, Berichtigung)
- Datenschutz-Folgenabschätzung durchführen

#### 📦 Komponenten
- `GDPRService` für Datenexport/Löschung
- API-Endpunkte für Betroffenenrechte
- Dokumentation der Datenverarbeitung

---

## 🔮 LOW Priority (2026) - Langfristige Massnahmen

### 8. **Multi-Factor Authentication** (A07)

**Status:** ❌ Nicht implementiert  
**Risiko:** Mittel  
**Aufwand:** ~4 Wochen  

#### 🎯 Ziele
- MFA für Superadmin
- Integration mit OIDC Provider MFA
- oder eigenständige TOTP-Implementierung

---

### 9. **Request Signing** (A04)

**Status:** ❌ Nicht implementiert  
**Risiko:** Niedrig  
**Aufwand:** ~2 Wochen  

#### 🎯 Ziele
- HMAC-Signing für Service-to-Service Kommunikation
- oder Mutual TLS (mTLS)

---

## 📊 Implementierungs-Timeline

### Q3 2025 (Juli - September)

| Woche | Aufgabe | Team | Status |
|-------|---------|------|--------|
| 27 | Audit-Logging: Infrastruktur | Backend | ⏳ Geplant |
| 28 | Audit-Logging: Integration | Backend | ⏳ Geplant |
| 29 | Rate Limiting: Implementierung | Backend | ⏳ Geplant |
| 30 | CSRF-Schutz: Implementierung | Backend | ⏳ Geplant |
| 31 | Testing & Bugfixing | Backend | ⏳ Geplant |
| 32 | Staging Deployment | DevOps | ⏳ Geplant |
| 33 | Produktion Rollout | DevOps | ⏳ Geplant |
| 34 | Monitoring & Dokumentation | Security | ⏳ Geplant |

### Q4 2025 (Oktober - Dezember)

| Woche | Aufgabe | Team | Status |
|-------|---------|------|--------|
| 41 | Tenant-Isolation: Infrastruktur | Backend | ⏳ Geplant |
| 42 | Tenant-Isolation: Repositories | Backend | ⏳ Geplant |
| 43 | Tenant-Isolation: Validation | Backend | ⏳ Geplant |
| 44 | API-Key Rotation | Backend | ⏳ Geplant |
| 45 | Security Headers | Backend | ⏳ Geplant |
| 46 | DSGVO: Löschkonzept | Legal + Dev | ⏳ Geplant |
| 47 | Testing & Bugfixing | Backend | ⏳ Geplant |
| 48 | Staging Deployment | DevOps | ⏳ Geplant |
| 49 | Produktion Rollout | DevOps | ⏳ Geplant |

### 2026

| Quartal | Aufgabe | Team | Status |
|---------|---------|------|--------|
| Q1 | MFA Implementierung | Security | ⏳ Geplant |
| Q2 | Request Signing | Backend | ⏳ Geplant |

---

## 🎯 Erfolgsmetriken

### Security Metrics

| Metrik | Zielwert | Aktuell | Status |
|--------|----------|---------|--------|
| **OWASP Top 10 Compliance** | 10/10 | 6/10 | ⚠️ Verbesserung nötig |
| **CIS Controls Compliance** | 10/10 | 8/10 | ⚠️ Verbesserung nötig |
| **Critical Vulnerabilities** | 0 | 0 | ✅ Gut |
| **High Vulnerabilities** | < 5 | 0 | ✅ Gut |
| **Audit Log Coverage** | 100% | 0% | ❌ Kritisch |
| **Rate Limit Coverage** | 100% | 0% | ❌ Kritisch |
| **CSRF Protection Coverage** | 100% | 0% | ❌ Kritisch |
| **Tenant Isolation Coverage** | 100% | 50% | ⚠️ Teilweise |

### Performance Metrics

| Metrik | Zielwert | Messung |
|--------|----------|---------|
| **Audit-Logging Overhead** | < 5% | API Response Time |
| **Rate Limiting Overhead** | < 1ms | Request Latency |
| **CSRF Overhead** | < 0.5ms | Request Latency |
| **Tenant-Isolation Overhead** | < 2% | API Response Time |

---

## 📚 Dokumentation

### OpenSpec Spezifikationen

| Change | Priorität | Status | OpenSpec Pfad |
|--------|-----------|--------|---------------|
| implement-audit-logging | HIGH | ✅ Spezifiziert | `openspec/changes/implement-audit-logging/` |
| implement-rate-limiting | HIGH | ✅ Spezifiziert | `openspec/changes/implement-rate-limiting/` |
| implement-csrf-protection | HIGH | ✅ Spezifiziert | `openspec/changes/implement-csrf-protection/` |
| improve-tenant-isolation | HIGH | ✅ Spezifiziert | `openspec/changes/improve-tenant-isolation/` |
| introduce-non-functional-baseline | HIGH | ✅ Bestehend | `openspec/changes/introduce-non-functional-baseline/` |

### Verweise

- [Security Analyse](docs/security-analysis.md) - Detaillierte Bedrohungsanalyse
- [Security Baseline](docs/security-baseline.md) - Sicherheits-Baseline
- [Development Guide](development_guide.md) - Entwicklerhinweise
- [CLAUDE Guidelines](CLAUDE.md) - KI-Agenten Anweisungen

---

## 👥 Verantwortlichkeiten

| Rolle | Verantwortung | Team |
|-------|---------------|------|
| **Security Lead** | Gesamtverantwortung, Priorisierung | Security Team |
| **Backend Lead** | Implementierung Backend-Komponenten | Backend Team |
| **Frontend Lead** | Frontend Integration | Frontend Team |
| **DevOps Lead** | Deployment, Monitoring | DevOps Team |
| **QA Lead** | Testing, Qualitätssicherung | QA Team |

---

## 📞 Kontakt

- **Security Team:** <security@nak-district-planner.example>
- **Projektleiter:** <project-lead@nak-district-planner.example>
- **Slack Channel:** #security

---

## 🔄 Review & Updates

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|-----------|
| 1.0.0 | 2025-06-19 | Security Team | Initialversion |

**Nächste Review:** 2025-09-30 (nach Q3 2025)
**Klassifikation:** Intern - Nur für autorisiertes Personal

