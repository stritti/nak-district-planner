# Security Analyse - NAK District Planner

**Version:** 1.0.0  
**Datum:** 2025-06-19  
**Status:** Aktiv  
**Verantwortlich:** Security Team  

---

## 1. Einleitung

### 1.1 Zweck dieses Dokuments

Dieses Dokument bietet eine umfassende Security-Analyse des NAK District Planners. Es identifiziert Sicherheitsrisiken, bewertet deren Schweregrad und definiert Massnahmen zur Risikominimierung. Die Analyse basiert auf:

- Aktueller Codebasis (Stand: main Branch)
- Architekturentscheidungen aus `openspec/` und `docs/`
- Implementierten Sicherheitsmassnahmen
- Best Practices für Webanwendungen und API-Sicherheit

### 1.2 Geltungsbereich

Die Analyse umfasst:
- **Backend:** FastAPI-Anwendung mit Celery-Workern
- **Frontend:** Vue 3 SPA mit OIDC-Integration
- **Infrastruktur:** Docker Compose, PostgreSQL, Redis
- **Authentifizierung:** OIDC mit Keycloak/Authentik
- **Datenflüsse:** API-Kommunikation, Kalender-Synchronisation

### 1.3 Methodik

Verwendete Analysemethoden:
- **Code Review:** Manuelle Inspektion der Sicherheitsrelevanten Komponenten
- **Threat Modeling:** STRIDE-Methode für Bedrohungsidentifikation
- **Dependency Analysis:** Abhängigkeits-Scans (pip-audit, bun audit, CodeQL)
- **Architektur Review:** Bewertung der Sicherheitsarchitektur

---

## 2. Aktuelle Sicherheitsarchitektur

### 2.1 Authentifizierung & Autorisierung

| Komponente | Implementierung | Status |
|------------|----------------|--------|
| **OIDC Integration** | `OIDCAdapter` mit JWKS-Caching | ✅ Implementiert |
| **Token Validation** | JWT-Signatur, Issuer, Audience, Expiry | ✅ Implementiert |
| **PKCE Flow** | Authorization Code Flow mit PKCE | ✅ Implementiert |
| **Rollenmodell** | RBAC mit Hierarchie (VIEWER < PLANNER < CONGREGATION_ADMIN < DISTRICT_ADMIN) | ✅ Implementiert |
| **Membership Gate** | Scope-basierte Zugriffskontrolle | ✅ Implementiert |
| **Superadmin** | Konfigurierbar via `SUPERADMIN_SUB` | ✅ Implementiert |

**Stärken:**
- Provider-agnostische OIDC-Implementierung (Keycloak, Authentik)
- Mehrstufige Token-Validierung (JWT → userinfo → introspection Fallback)
- Feingranulare Berechtigungsprüfung auf Application-Layer
- Automatische Token-Refresh im Frontend

### 2.2 Datenschutz

| Massnahme | Implementierung | Status |
|-----------|----------------|--------|
| **Credential Encryption** | Fernet (AES-128-CBC) mit SHA-256 Key Derivation | ✅ Implementiert |
| **Secret Management** | `.env` Dateien (gitignored) | ✅ Implementiert |
| **HTTPS Enforcement** | Reverse Proxy Konfiguration | ⚠️ Teilweise (abhängig von Deployment) |
| **Sensitive Data Handling** | Keine Secrets in Logs/Errors | ✅ Implementiert |

**Stärken:**
- Service-Layer-Verschlüsselung für Kalender-Credentials
- Keine Plaintext-Speicherung von OAuth-Tokens
- Fehlerbehandlung ohne Stack Traces in Produktion

### 2.3 Netzwerksicherheit

| Massnahme | Implementierung | Status |
|-----------|----------------|--------|
| **Port Exposition** | Entwicklungsports exponiert, Produktion isoliert | ✅ Konfiguriert |
| **CORS** | Restriktiv konfigurierbar | ⚠️ Standardmäßig locker in Entwicklung |
| **Interne Kommunikation** | Docker-Netzwerk mit Service-Namen | ✅ Implementiert |
| **Firewall Rules** | Nicht im Projekt, Host-Verantwortung | ❌ Nicht im Scope |

### 2.4 API-Sicherheit

| Massnahme | Implementierung | Status |
|-----------|----------------|--------|
| **API Key Auth** | `X-API-Key` Header für Service-to-Service | ✅ Implementiert |
| **JWT Bearer Auth** | `Authorization: Bearer` für User-Aktionen | ✅ Implementiert |
| **Rate Limiting** | Geplant für öffentliche Endpunkte | ❌ Nicht implementiert |
| **Input Validation** | Pydantic v2 Models | ✅ Implementiert |

---

## 3. Bedrohungsanalyse (STRIDE)

### 3.1 Spoofing (Identitätsfälschung)

| ID | Bedrohung | Risiko | Betroffene Komponenten | Status | Massnahmen |
|----|-----------|--------|----------------------|--------|------------|
| **SEC-001** | Angreifer gibt sich als legitimer Benutzer aus | **Hoch** | OIDC Auth, API Endpunkte | ⚠️ Teilweise geschützt | JWT-Validierung, PKCE Flow |
| **SEC-002** | API-Key Kompromittierung | **Hoch** | Service-to-Service Kommunikation | ⚠️ Teilweise geschützt | API-Key in `.env`, aber keine Rotation |
| **SEC-003** | Session Hijacking | **Mittel** | Frontend Session Storage | ✅ Geschützt | PKCE Verifier in Session Storage (auto-cleared) |
| **SEC-004** | CSRF-Angriffe | **Niedrig** | Formulare, State-changing Requests | ❌ Nicht geschützt | Kein CSRF-Token implementiert |

**Empfehlungen:**
- [ ] CSRF-Tokens für state-changing Requests implementieren (PRIORITY: HIGH)
- [ ] API-Key Rotation Mechanismus einführen (PRIORITY: MEDIUM)
- [ ] Token-Bindung an IP/Device für sensible Operationen (PRIORITY: LOW)

### 3.2 Tampering (Manipulation)

| ID | Bedrohung | Risiko | Betroffene Komponenten | Status | Massnahmen |
|----|-----------|--------|----------------------|--------|------------|
| **SEC-005** | Manipulation von Request-Daten | **Hoch** | API Input, Formulardaten | ✅ Geschützt | Pydantic v2 Validation |
| **SEC-006** | Manipulation von Export-Tokens | **Mittel** | ICS-Export Endpunkte | ⚠️ Teilweise geschützt | Token-Validierung, aber keine Rate-Limiting |
| **SEC-007** | Manipulation von Kalender-Daten | **Mittel** | Sync-Operationen | ✅ Geschützt | Hash-basierte Deduplizierung |
| **SEC-008** | Manipulation von Datenbank-Inhalten | **Hoch** | Direkter DB-Zugriff | ⚠️ Teilweise geschützt | SQLAlchemy ORM, aber keine Row-Level Security |

**Empfehlungen:**
- [ ] Rate Limiting für öffentliche Export-Endpunkte (PRIORITY: HIGH)
- [ ] Row-Level Security (RLS) in PostgreSQL für Multi-Tenancy (PRIORITY: MEDIUM)
- [ ] Request-Signing für kritische API-Calls (PRIORITY: LOW)

### 3.3 Repudiation (Abstreitbarkeit)

| ID | Bedrohung | Risiko | Betroffene Komponenten | Status | Massnahmen |
|----|-----------|--------|----------------------|--------|------------|
| **SEC-009** | Benutzer streitet Aktionen ab | **Mittel** | Alle schreibenden Operationen | ❌ Nicht geschützt | Kein Audit-Logging |
| **SEC-010** | Administrator streitet Konfiguration ab | **Mittel** | Admin-Operationen | ❌ Nicht geschützt | Kein Audit-Trail |

**Empfehlungen:**
- [ ] Audit-Logging für alle schreibenden Operationen (PRIORITY: HIGH)
- [ ] Unveränderliche Logs mit Benutzer- und Zeitstempel (PRIORITY: HIGH)
- [ ] Regelmäßige Log-Analyse und Alerting (PRIORITY: MEDIUM)

### 3.4 Information Disclosure (Informatiionspreisgabe)

| ID | Bedrohung | Risiko | Betroffene Komponenten | Status | Massnahmen |
|----|-----------|--------|----------------------|--------|------------|
| **SEC-011** | Exposure von sensiblen Daten in Fehlermeldungen | **Hoch** | API Error Responses | ✅ Geschützt | Generische Fehlermeldungen in Produktion |
| **SEC-012** | Exposure von Credentials in Logs | **Hoch** | Logging | ✅ Geschützt | Keine Credentials in Logs |
| **SEC-013** | Exposure von Benutzerdaten in ICS-Export | **Mittel** | Öffentliche Kalender-Exporte | ⚠️ Teilweise geschützt | Anonymisierung für PUBLIC Tokens |
| **SEC-014** | Directory Traversal | **Niedrig** | Dateizugriff | ✅ Geschützt | Kein Dateizugriff implementiert |
| **SEC-015** | Timing Attacks | **Niedrig** | Authentifizierung | ⚠️ Nicht geschützt | Keine Constant-Time Comparisons |

**Empfehlungen:**
- [ ] Constant-Time String Comparison für Token-Validierung (PRIORITY: MEDIUM)
- [ ] Regelmäßige Security-Header Überprüfung (PRIORITY: LOW)

### 3.5 Denial of Service (DoS)

| ID | Bedrohung | Risiko | Betroffene Komponenten | Status | Massnahmen |
|----|-----------|--------|----------------------|--------|------------|
| **SEC-016** | Ressourcen-Erschöpfung durch viele Requests | **Hoch** | API Endpunkte | ❌ Nicht geschützt | Kein Rate Limiting |
| **SEC-017** | Datenbank-Überlastung | **Hoch** | Komplexe Queries | ⚠️ Teilweise geschützt | Pagination implementiert |
| **SEC-018** | Celery-Queue Überlastung | **Mittel** | Hintergrundaufgaben | ❌ Nicht geschützt | Keine Queue-Limits |
| **SEC-019** | Memory Exhaustion durch große Payloads | **Mittel** | API Requests | ⚠️ Teilweise geschützt | FastAPI Request Size Limits |

**Empfehlungen:**
- [ ] Rate Limiting für alle öffentlichen Endpunkte (PRIORITY: HIGH)
- [ ] Celery Rate Limits und Queue-Limits konfigurieren (PRIORITY: MEDIUM)
- [ ] Request Size Limits für Uploads/Exporte (PRIORITY: MEDIUM)
- [ ] Datenbank-Query Timeout konfigurieren (PRIORITY: MEDIUM)

### 3.6 Elevation of Privilege (Rechteerweiterung)

| ID | Bedrohung | Risiko | Betroffene Komponenten | Status | Massnahmen |
|----|-----------|--------|----------------------|--------|------------|
| **SEC-020** | Benutzer erhält höhere Rechte | **Kritisch** | Rollenverwaltung | ⚠️ Teilweise geschützt | RBAC implementiert, aber keine Scope-Validation |
| **SEC-021** | Cross-Tenant Data Access | **Kritisch** | Multi-Tenancy | ⚠️ Teilweise geschützt | Membership-Gate, aber keine Tenant-Isolation |
| **SEC-022** | Privilege Escalation durch ID-Manipulation | **Hoch** | API Endpunkte mit ID-Parametern | ✅ Geschützt | Berechtigungsprüfung auf Application-Layer |
| **SEC-023** | Superadmin-Rechte Missbrauch | **Hoch** | Superadmin-Funktionen | ⚠️ Teilweise geschützt | Konfigurierbar, aber keine MFA |

**Empfehlungen:**
- [ ] Tenant-Isolation auf Datenbank-Ebene (RLS) (PRIORITY: HIGH)
- [ ] Scope-Validation für alle Admin-Operationen (PRIORITY: HIGH)
- [ ] Multi-Factor Authentication für Superadmin (PRIORITY: MEDIUM)
- [ ] Regelmäßige Berechtigungs-Reviews (PRIORITY: MEDIUM)

---

## 4. Risikobewertung

### 4.1 Risikomatrix

| Risiko | Eintrittswahrscheinlichkeit | Auswirkung | Risikostufe | Priorität |
|--------|---------------------------|------------|-------------|-----------|
| **Kritisch** | Hoch | Hoch | **Kritisch** | SOFORT |
| **Hoch** | Hoch | Mittel | **Hoch** | HOCH |
| **Hoch** | Mittel | Hoch | **Hoch** | HOCH |
| **Mittel** | Hoch | Niedrig | **Mittel** | MEDIUM |
| **Mittel** | Mittel | Mittel | **Mittel** | MEDIUM |
| **Niedrig** | Niedrig | Hoch | **Mittel** | MEDIUM |

### 4.2 Top 10 Sicherheitsrisiken

| Rang | ID | Risiko | Risikostufe | Priorität | Status |
|------|----|--------|-------------|-----------|--------|
| 1 | SEC-009 | Fehlendes Audit-Logging | Hoch | **HIGH** | ❌ Nicht implementiert |
| 2 | SEC-016 | Kein Rate Limiting | Hoch | **HIGH** | ❌ Nicht implementiert |
| 3 | SEC-020 | Elevation of Privilege | Kritisch | **HIGH** | ⚠️ Teilweise |
| 4 | SEC-021 | Cross-Tenant Data Access | Kritisch | **HIGH** | ⚠️ Teilweise |
| 5 | SEC-004 | CSRF-Angriffe | Hoch | **HIGH** | ❌ Nicht implementiert |
| 6 | SEC-001 | Identitätsfälschung | Hoch | **HIGH** | ⚠️ Teilweise |
| 7 | SEC-002 | API-Key Kompromittierung | Hoch | MEDIUM | ⚠️ Teilweise |
| 8 | SEC-019 | Memory Exhaustion | Mittel | MEDIUM | ⚠️ Teilweise |
| 9 | SEC-013 | Informationspreisgabe in Exports | Mittel | MEDIUM | ⚠️ Teilweise |
| 10 | SEC-008 | Datenbank-Manipulation | Hoch | MEDIUM | ⚠️ Teilweise |

---

## 5. Sicherheitsmassnahmen

### 5.1 Sofortmassnahmen (Priorität: HIGH)

#### 5.1.1 Audit-Logging implementieren

**Problem:** Aktuell gibt es kein Audit-Logging für schreibende Operationen.  
**Lösung:**

```python
# Beispiel-Implementierung für Audit-Logging
from datetime import UTC, datetime
import json
import logging
from typing import Any
import uuid

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")
        
    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        user_sub: str | None = None,
        changes: dict[str, Any] | None = None,
        status: str = "success",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        audit_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "user_sub": user_sub,
            "changes": json.dumps(changes) if changes else None,
            "status": status,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        self.logger.info(json.dumps(audit_entry))
```

**Umsetzung:**
- [ ] Audit-Logger Modul erstellen
- [ ] Middleware für Request-Logging
- [ ] Dekorator für schreibende Operationen
- [ ] Log-Retention Policy definieren

#### 5.1.2 Rate Limiting implementieren

**Problem:** Öffentliche Endpunkte (z.B. ICS-Export) haben kein Rate Limiting.  
**Lösung:**

```python
# Beispiel mit FastAPI + Redis
from fastapi import Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from datetime import timedelta

class RateLimiter:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        
    async def check_rate_limit(
        self,
        key: str,
        limit: int = 100,
        window_seconds: int = 60,
    ) -> tuple[bool, dict]:
        redis_key = f"rate_limit:{key}"
        current = await self.redis.get(redis_key)
        
        if current and int(current) >= limit:
            ttl = await self.redis.ttl(redis_key)
            return False, {
                "retry_after": ttl,
                "limit": limit,
                "remaining": 0,
            }
        
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds)
        await pipe.execute()
        
        current_count = await self.redis.get(redis_key)
        return True, {
            "limit": limit,
            "remaining": limit - int(current_count),
            "reset": window_seconds,
        }
```

**Konfiguration:**
```python
# In FastAPI Middleware
RATE_LIMITS = {
    "/api/v1/export/*/calendar.ics": {"limit": 60, "window": 60},  # 60 Requests/Minute
    "/api/v1/events": {"limit": 100, "window": 60},
    "default": {"limit": 200, "window": 60},
}
```

#### 5.1.3 CSRF-Schutz implementieren

**Problem:** Kein CSRF-Schutz für state-changing Requests.  
**Lösung:**

```python
# CSRF-Middleware für FastAPI
from fastapi import Request, HTTPException, status
import secrets
import hmac
import hashlib

class CSRFMiddleware:
    def __init__(self, app, secret_key: str, cookie_name: str = "csrf_token"):
        self.app = app
        self.secret_key = secret_key
        self.cookie_name = cookie_name
        
    async def __call__(self, request: Request, call_next):
        # Skip for GET, HEAD, OPTIONS
        if request.method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)
            return response
            
        # Verify CSRF token for state-changing requests
        csrf_token = request.cookies.get(self.cookie_name)
        csrf_header = request.headers.get("X-CSRF-Token")
        
        if not csrf_token or not csrf_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing",
            )
            
        if not self._validate_csrf_token(csrf_token, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token invalid",
            )
            
        response = await call_next(request)
        return response
        
    def _validate_csrf_token(self, token: str, header: str) -> bool:
        expected = hmac.new(
            self.secret_key.encode(),
            token.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, header)
```

### 5.2 Mittelfristige Massnahmen (Priorität: MEDIUM)

#### 5.2.1 Row-Level Security (RLS) in PostgreSQL

**Problem:** Keine Datenbank-Ebene Tenant-Isolation.  
**Lösung:**

```sql
-- Beispiel RLS Policy für Events
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- District Admin kann alle Events im eigenen Bezirk sehen
CREATE POLICY district_admin_policy ON events
    FOR SELECT USING (
        district_id = current_setting('app.current_district_id')::uuid
    );

-- Planner kann nur published Events sehen
CREATE POLICY planner_policy ON events
    FOR SELECT USING (
        district_id = current_setting('app.current_district_id')::uuid
        AND status = 'PUBLISHED'
    );
```

**Implementierung:**
- [ ] RLS Policies für alle Tenant-spezifischen Tabellen
- [ ] Middleware zur Setzung von `app.current_district_id`
- [ ] Tests für RLS-Policies

#### 5.2.2 API-Key Rotation

**Problem:** API-Keys werden nicht rotiert.  
**Lösung:**

```python
# API-Key Management mit Rotation
from datetime import UTC, datetime, timedelta
import secrets
import hashlib

class APIKeyManager:
    def __init__(self, rotation_interval_days: int = 90):
        self.rotation_interval = timedelta(days=rotation_interval_days)
        
    def generate_key(self) -> tuple[str, str]:
        """Generate raw key and its hash for storage."""
        raw_key = secrets.token_hex(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, key_hash
        
    def is_key_expired(self, created_at: datetime) -> bool:
        """Check if key should be rotated."""
        return (datetime.now(UTC) - created_at) >= self.rotation_interval
        
    def validate_key(self, raw_key: str, stored_hash: str) -> bool:
        """Validate key against stored hash."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return hmac.compare_digest(key_hash, stored_hash)
```

#### 5.2.3 Tenant-Isolation verbessern

**Problem:** Cross-Tenant Data Access möglich.  
**Lösung:**

```python
# Tenant-Context Middleware
from contextvars import ContextVar
from typing import Optional
import uuid

tenant_id_var: ContextVar[Optional[uuid.UUID]] = ContextVar("tenant_id", default=None)

class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant from JWT or API key
        tenant_id = self._extract_tenant_id(request)
        token = tenant_id_var.set(tenant_id)
        
        try:
            response = await call_next(request)
            return response
        finally:
            tenant_id_var.reset(token)
            
    def _extract_tenant_id(self, request: Request) -> uuid.UUID | None:
        # From JWT token
        if hasattr(request.state, "user"):
            return request.state.user.current_district_id
        # From API key
        if hasattr(request.state, "api_key"):
            return request.state.api_key.district_id
        return None
```

### 5.3 Langfristige Massnahmen (Priorität: LOW)

#### 5.3.1 Multi-Factor Authentication (MFA)

**Problem:** Superadmin hat keine zusätzliche Authentifizierung.  
**Lösung:**
- Integration mit OIDC Provider MFA
- oder eigenständige MFA-Implementierung (TOTP)

#### 5.3.2 Security Headers

**Problem:** Fehlende Security Headers.  
**Lösung:**

```python
# Security Headers Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' https://oidc.example.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # Other security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=()"
        )
        
        return response
```

#### 5.3.3 Request Signing

**Problem:** Keine Request-Signing für kritische API-Calls.  
**Lösung:**
- HMAC-Signing für Service-to-Service Kommunikation
- oder Mutual TLS (mTLS)

---

## 6. Dependency Security

### 6.1 Aktuelle Abhängigkeiten

**Backend (Python):**
- FastAPI, Starlette, Uvicorn
- SQLAlchemy, asyncpg, Alembic
- Celery, Redis
- PyJWT, Authlib, httpx
- cryptography, defusedxml
- opentelemetry-*

**Frontend (JavaScript/TypeScript):**
- Vue 3, Vite, Pinia
- Tailwind CSS
- OIDC Client Library

### 6.2 Security Scans

**Automatisierte Scans:**
- **CodeQL:** Statische Code-Analyse (Python, JavaScript)
- **pip-audit:** Python Dependency Vulnerability Scan
- **bun audit:** JavaScript/TypeScript Dependency Scan

**Manuelle Reviews:**
- Regelmäßige Überprüfung der Abhängigkeiten
- Risikoeinschätzung für neue Dependencies

### 6.3 Bekannte Vulnerabilities

| Dependency | Version | CVE | Status | Massnahme |
|------------|---------|-----|--------|-----------|
| *Keine bekannten* | - | - | ✅ Clean | - |

**Hinweis:** Aktuelle Scan-Ergebnisse zeigen keine kritischen Vulnerabilities. Regelmäßige Scans werden durch GitHub Actions sichergestellt.

---

## 7. Compliance & Best Practices

### 7.1 OWASP Top 10

| OWASP Kategorie | Status | Massnahmen |
|----------------|--------|------------|
| **A01:2021 - Broken Access Control** | ⚠️ Teilweise | RBAC implementiert, aber Tenant-Isolation unvollständig |
| **A02:2021 - Cryptographic Failures** | ✅ Gut | Fernet Encryption, JWT Validation |
| **A03:2021 - Injection** | ✅ Gut | SQLAlchemy ORM, Pydantic Validation |
| **A04:2021 - Insecure Design** | ⚠️ Teilweise | Architektur gut, aber einige Security-Features fehlen |
| **A05:2021 - Security Misconfiguration** | ⚠️ Teilweise | Security Headers fehlen, Rate Limiting fehlt |
| **A06:2021 - Vulnerable and Outdated Components** | ✅ Gut | Automatisierte Dependency Scans |
| **A07:2021 - Identification and Authentication Failures** | ⚠️ Teilweise | OIDC gut, aber MFA fehlt |
| **A08:2021 - Software and Data Integrity Failures** | ✅ Gut | Hash-basierte Deduplizierung, Request Validation |
| **A09:2021 - Security Logging and Monitoring Failures** | ❌ Kritisch | Kein Audit-Logging |
| **A10:2021 - Server-Side Request Forgery (SSRF)** | ✅ Gut | Keine direkte URL-Fetching von User-Input |

### 7.2 CIS Controls

| Control | Status | Priorität |
|---------|--------|-----------|
| **CIS 1 - Inventory and Control of Enterprise Assets** | ✅ Gut | - |
| **CIS 2 - Inventory and Control of Software Assets** | ✅ Gut | - |
| **CIS 3 - Data Protection** | ⚠️ Teilweise | Encryption gut, aber Backup-Testing fehlt |
| **CIS 4 - Secure Configuration of Enterprise Assets** | ⚠️ Teilweise | Security Headers fehlen |
| **CIS 5 - Account Management** | ⚠️ Teilweise | MFA fehlt |
| **CIS 6 - Access Control Management** | ⚠️ Teilweise | RBAC gut, aber Tenant-Isolation unvollständig |
| **CIS 7 - Continuous Vulnerability Management** | ✅ Gut | Automatisierte Scans |
| **CIS 8 - Audit Log Management** | ❌ Kritisch | Kein Audit-Logging |

### 7.3 DSGVO / GDPR

| Anforderung | Status | Massnahmen |
|-------------|--------|------------|
| **Datenminimierung** | ✅ Gut | Nur notwendige Daten werden gespeichert |
| **Zweckbindung** | ✅ Gut | Daten werden nur für definierte Zwecke genutzt |
| **Löschkonzept** | ⚠️ Teilweise | Soft-Delete implementiert, aber keine automatische Löschung |
| **Betroffenenrechte** | ❌ Nicht implementiert | Export, Löschung, Berichtigung fehlen |
| **Datenschutz-Folgenabschätzung** | ❌ Nicht durchgeführt | - |

---

## 8. Incident Response

### 8.1 Security Incident Klassifikation

| Schweregrad | Beschreibung | Reaktionszeit |
|-------------|--------------|---------------|
| **Kritisch** | Aktiver Angriff, Datenkompromittierung | Sofort (< 1 Stunde) |
| **Hoch** | Potenzielle Kompromittierung, hohe Auswirkung | < 4 Stunden |
| **Mittel** | Sicherheitsvorfall mit begrenzter Auswirkung | < 24 Stunden |
| **Niedrig** | Sicherheitsrelevantes Ereignis | < 72 Stunden |

### 8.2 Incident Response Procedure

1. **Detection & Triage**
   - Automatisierte Alerts (z.B. ungewöhnliche Login-Versuche)
   - Manuelle Meldungen (z.B. durch Benutzer)
   - Klassifikation des Incidents

2. **Containment**
   - Isolierung betroffener Systeme
   - Deaktivierung kompromittierter Accounts
   - Netzwerk-Segmentierung

3. **Eradication**
   - Entfernung von Malware/Backdoors
   - Patch Management
   - Credential Rotation

4. **Recovery**
   - System-Wiederherstellung aus Backups
   - Validierung der Systemintegrität
   - schrittweise Wiederinbetriebnahme

5. **Lessons Learned**
   - Post-Mortem Analyse
   - Dokumentation der Massnahmen
   - Verbesserung der Sicherheitsmassnahmen

### 8.3 Kontaktinformationen

| Rolle | Kontakt | Verantwortung |
|-------|---------|---------------|
| Security Team | <security@nak-district-planner.example> | Incident Response |
| Projektleiter | <project-lead@nak-district-planner.example> | Koordination |
| Hosting Provider | <support@hosting-provider.example> | Infrastruktur |

---

## 9. Monitoring & Metriken

### 9.1 Security Metriken

| Metrik | Beschreibung | Zielwert | Aktueller Status |
|--------|--------------|----------|------------------|
| **Vulnerability Scan Coverage** | % der Codebasis mit Security Scans | 100% | 100% |
| **Critical Vulnerabilities** | Anzahl kritischer Schwachstellen | 0 | 0 |
| **High Vulnerabilities** | Anzahl hoher Schwachstellen | < 5 | 0 |
| **Mean Time to Patch** | Durchschnittliche Zeit bis zum Patch | < 7 Tage | - |
| **Security Test Coverage** | Testabdeckung für Security-Features | > 80% | ~60% |

### 9.2 Alerting

| Alert | Schwelle | Kanäle |
|-------|----------|--------|
| **Failed Login Attempts** | > 5 in 1 Minute | Slack, Email |
| **Rate Limit Exceeded** | > 100 Requests/Minute | Slack |
| **Authentication Errors** | > 10 in 5 Minuten | Slack |
| **Database Connection Failures** | > 3 in 1 Minute | PagerDuty |
| **High Error Rate** | > 10% in 5 Minuten | PagerDuty |

---

## 10. Roadmap & Priorisierung

### 10.1 Priorisierte Massnahmen

| Priorität | Massnahme | Aufwand | Zeitrahmen | Verantwortlich |
|-----------|----------|---------|------------|----------------|
| **HIGH** | Audit-Logging implementieren | Mittel | Q3 2025 | Backend Team |
| **HIGH** | Rate Limiting für öffentliche Endpunkte | Niedrig | Q3 2025 | Backend Team |
| **HIGH** | CSRF-Schutz implementieren | Niedrig | Q3 2025 | Backend Team |
| **HIGH** | Tenant-Isolation verbessern (RLS) | Hoch | Q4 2025 | Backend Team |
| **MEDIUM** | API-Key Rotation | Mittel | Q4 2025 | Backend Team |
| **MEDIUM** | Security Headers | Niedrig | Q3 2025 | Backend Team |
| **MEDIUM** | DSGVO Compliance (Löschkonzept) | Mittel | Q4 2025 | Legal + Dev |
| **LOW** | Multi-Factor Authentication | Hoch | 2026 | Security Team |
| **LOW** | Request Signing | Mittel | 2026 | Backend Team |

### 10.2 Meilensteine

- **Q3 2025:** Kritische Sicherheitslücken schliessen (Audit-Logging, Rate Limiting, CSRF)
- **Q4 2025:** Tenant-Isolation und API-Security verbessern
- **2026:** Erweiterte Sicherheitsfeatures (MFA, Request Signing)

---

## 11. Anhang

### 11.1 Glossar

| Begriff | Definition |
|---------|------------|
| **OIDC** | OpenID Connect - Authentifizierungsprotokoll basierend auf OAuth 2.0 |
| **PKCE** | Proof Key for Code Exchange - Sicherheitserweiterung für OAuth 2.0 |
| **JWKS** | JSON Web Key Set - Öffentliche Schlüssel für JWT-Validierung |
| **RBAC** | Role-Based Access Control - Rollenbasierte Zugriffskontrolle |
| **RLS** | Row-Level Security - Zeilenbasierte Sicherheit in PostgreSQL |
| **CSRF** | Cross-Site Request Forgery - Angriff durch gefälschte Requests |
| **XSS** | Cross-Site Scripting - Einspritzen von Skriptcode |
| **DoS** | Denial of Service - Dienstverweigerungsangriff |
| **MFA** | Multi-Factor Authentication - Mehrfaktor-Authentifizierung |

### 11.2 Referenzen

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CIS Controls v8](https://www.cisecurity.org/controls/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [GDPR / DSGVO](https://gdpr-info.eu/)

### 11.3 Dokumentenhistorie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|-----------|
| 1.0.0 | 2025-06-19 | Security Team | Initialversion |

---

**Dokumentenverantwortlich:** Security Team  
**Nächste Review:** 2025-12-19  
**Klassifikation:** Intern - Nur für autorisiertes Personal
