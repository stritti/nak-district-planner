# Security Baseline

**Version:** 2.0.0  
**Datum:** 2025-06-19  
**Status:** Aktiv  
**Verantwortlich:** Security Team  

> **Hinweis:** Dieses Dokument definiert die verbindlichen Sicherheitsleitplanken. 
> Detaillierte Analysen und Implementierungsanleitungen finden sich in `docs/security-analysis.md`.

---

## 1. Authentifizierung und Autorisierung

### 1.1 Anforderungen

- ✅ **OIDC (Authorization Code Flow mit PKCE)** fuer Frontend-Login implementiert.
- ✅ **Token-Validierung** im Backend via JWKS, inkl. Issuer-/Audience-/Expiry-Pruefung.
- ✅ **Rollen und Scopes** gemaess `docs/roles.md` implementiert.
- ✅ **Membership-Gate** fuer geschuetzte Endpunkte gemaess `docs/approval-workflow.md` implementiert.

### 1.2 Implementierungsdetails

**OIDC-Adapter (`app/adapters/auth/oidc.py`):**
- Provider-agnostische Implementierung (Keycloak, Authentik, Okta, etc.)
- JWKS-Caching mit 1-Stunden TTL und Fallback auf Cache bei Fehlern
- Mehrstufige Token-Validierung: JWT → userinfo → introspection
- Automatische Clock-Skew Toleranz (120 Sekunden)

**Berechtigungsprüfung (`app/adapters/auth/permissions.py`):**
- Rollenhierarchie: VIEWER (1) < PLANNER (2) < CONGREGATION_ADMIN (3) < DISTRICT_ADMIN (4)
- Scope-basierte Zugriffskontrolle (District und Congregation)
- Superadmin-Bypass für systemweite Operationen

**Wichtige Endpunkte:**
- `GET /api/v1/auth/oidc/discovery` - OIDC Discovery (unauthentifiziert)
- `POST /api/v1/auth/oidc/token` - Token Exchange (unauthentifiziert)
- `GET /api/v1/auth/me` - Current User Info (authentifiziert)
- `GET /api/v1/auth/access` - Access Context mit Memberships (authentifiziert)

### 1.3 Compliance-Checks

- [ ] Alle geschützten Endpunkte erfordern gültige Authentifizierung
- [ ] Alle schreibenden Operationen erfordern Berechtigungsprüfung
- [ ] Cross-Tenant Zugriff ist verhindert
- [ ] Token-Validierung umfasst Signatur, Issuer, Audience, Expiry

---

## 2. Daten- und Geheimnisschutz

### 2.1 Anforderungen

- ✅ **API-Keys, Client-Secrets und Zugangsdaten** niemals im Repository speichern.
- ✅ **Sensible Konfiguration** nur ueber `.env` / Secret-Management.
- ✅ **Externe Kalender-Credentials** verschluesselt speichern (Service-Layer-Verschluesselung).

### 2.2 Implementierungsdetails

**Credential Encryption (`app/application/crypto.py`):**
- Algorithmus: Fernet (AES-128-CBC)
- Key Derivation: SHA-256 Hash von `settings.secret_key`
- Format: Base64url-encoded Fernet Tokens
- Fehlerbehandlung: `CryptoError` mit deutschen Fehlermeldungen

**Verwendungsmuster:**
```python
from app.application.crypto import encrypt_credentials, decrypt_credentials

# Verschlüsseln vor dem Speichern
encrypted = encrypt_credentials({"api_key": "...", "url": "..."})

# Entschlüsseln beim Lesen
credentials = decrypt_credentials(encrypted)
```

**Warnung:** Ändern von `SECRET_KEY` macht alle verschlüsselten Daten unlesbar!

### 2.3 Datenklassifizierung

| Datenkategorie | Schutzbedarf | Massnahmen |
|---------------|--------------|-----------|
| **Secrets** (API-Keys, Passwords, Tokens) | **Kritisch** | Verschlüsselung, kein Logging, kein Commit |
| **Auth-Tokens** (JWT, Session Tokens) | **Hoch** | HTTPS, kurze Lebensdauer, sichere Speicherung |
| **Benutzerdaten** (E-Mail, Name, Rollen) | **Mittel** | Zugriffskontrolle, DSGVO-konform |
| **Kalenderdaten** (Events, Assignments) | **Mittel** | Tenant-Isolation, Zugriffskontrolle |
| **Systemdaten** (Logs, Metriken) | **Niedrig** | Keine sensiblen Daten enthalten |

### 2.4 Compliance-Checks

- [ ] Alle Secrets werden verschlüsselt gespeichert
- [ ] Keine Secrets in Code, Logs oder Error Messages
- [ ] `.env` Dateien sind gitignored
- [ ] Produktions-Secrets werden über Secret-Manager bereitgestellt

---

## 3. Transport- und Netzwerksicherheit

### 3.1 Anforderungen

- ✅ **Produktion nur ueber HTTPS** (TLS-Termination am Reverse Proxy).
- ✅ **Interne Dienste** (DB, Redis, Backend-Port) nicht oeffentlich exponieren.
- ⚠️ **CORS** restriktiv konfigurieren (in Entwicklung locker).

### 3.2 Implementierungsdetails

**Produktionskonfiguration:**
- Backend-Port (8000) nicht nach außen exponiert
- Datenbank-Port (5432) nicht nach außen exponiert
- Redis-Port (6379) nicht nach außen exponiert
- Alle Services kommunizieren über internes Docker-Netzwerk

**Reverse Proxy Beispiel (nginx):**
```nginx
server {
    listen 443 ssl;
    server_name planer.example.de;
    
    ssl_certificate /etc/letsencrypt/live/planer.example.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/planer.example.de/privkey.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### 3.3 Compliance-Checks

- [ ] HTTPS ist in Produktion aktiviert
- [ ] Interne Ports sind nicht öffentlich zugänglich
- [ ] CORS ist in Produktion restriktiv konfiguriert
- [ ] Security Headers sind konfiguriert

---

## 4. API-Schutz

### 4.1 Anforderungen

- ✅ **Geschuetzte Endpunkte** erfordern gueltige Authentifizierung.
- ❌ **Oeffentliche Endpunkte** (z. B. ICS-Export) erhalten Rate-Limiting (Roadmap).
- ✅ **Sicherheitsrelevante Fehler** werden ohne sensitive Interna ausgeliefert.

### 4.2 Authentifizierungsmethoden

| Methode | Verwendung | Header | Status |
|---------|-----------|--------|--------|
| **JWT Bearer** | Benutzer-Aktionen | `Authorization: Bearer <token>` | ✅ Implementiert |
| **API Key** | Service-to-Service | `X-API-Key: <key>` | ✅ Implementiert |
| **Export Token** | Öffentlicher Kalender-Export | URL-Parameter | ✅ Implementiert |

### 4.3 Endpunkt-Klassifizierung

| Endpunkt | Authentifizierung | Zugriff | Rate Limiting |
|----------|------------------|---------|---------------|
| `/api/health` | Keine | Öffentlich | ❌ Nein |
| `/api/v1/auth/oidc/discovery` | Keine | Öffentlich | ❌ Nein |
| `/api/v1/auth/oidc/token` | Keine | Öffentlich | ❌ Nein |
| `/api/v1/auth/me` | JWT Bearer | Authentifiziert | ❌ Nein |
| `/api/v1/events` | JWT Bearer | Authentifiziert | ❌ Nein |
| `/api/v1/export/{token}/calendar.ics` | Export Token | Öffentlich | ❌ **Fehlt!** |

### 4.4 Compliance-Checks

- [ ] Alle geschützten Endpunkte erfordern Authentifizierung
- [ ] API Keys werden sicher gespeichert und rotiert
- [ ] Rate Limiting ist für öffentliche Endpunkte implementiert
- [ ] Input Validation ist für alle Endpunkte implementiert

---

## 5. Supply-Chain und statische Scans

### 5.1 Anforderungen

- ✅ **Security-Workflow** nutzt CodeQL, pip-audit und bun audit (siehe `.github/workflows/security.yml`).
- ✅ **PRs mit neuen Dependencies** erfordern kurze Risikoeinschaetzung.

### 5.2 Automatisierte Scans

**GitHub Actions Workflow:**
- **CodeQL:** Statische Code-Analyse für Python und JavaScript/TypeScript
  - Ausführung: Bei Push auf main/develop, PRs, und wöchentlich (Montags 08:00 UTC)
  - Sprachen: Python, JavaScript/TypeScript
  - Queries: security-and-quality

- **pip-audit:** Python Dependency Vulnerability Scan
  - Ausführung: Bei jedem Push/PR
  - Datenbank: OSV (Open Source Vulnerabilities)

- **bun audit:** JavaScript/TypeScript Dependency Scan
  - Ausführung: Bei jedem Push/PR
  - Level: moderate (Standard)

### 5.3 Manuelle Reviews

**Dependency Review Prozess:**
1. Popularität und Wartungsstatus prüfen
2. Sicherheitshistorie analysieren
3. Lizenzkompatibilität verifizieren
4. Risikoeinschätzung dokumentieren
5. Entscheidung im PR begrunden

### 5.4 Compliance-Checks

- [ ] Alle Dependencies sind in pyproject.toml/package.json deklariert
- [ ] Keine direkten `pip install` oder `npm install` im Code
- [ ] Security Scans laufen erfolgreich durch
- [ ] Neue Dependencies haben Risikoeinschätzung

---

## 6. Audit und Nachvollziehbarkeit

### 6.1 Anforderungen

- ⚠️ **Governance-relevante Aktionen** sollen auditierbar sein.
- ❌ **Vollstaendige Audit-Log-Abdeckung** ist als priorisierte Roadmap-Massnahme definiert.

### 6.2 Audit-Logging Anforderungen

**Zu loggende Ereignisse:**
- Alle schreibenden Operationen (CREATE, UPDATE, DELETE)
- Alle Authentifizierungsversuche (erfolgreich und fehlgeschlagen)
- Alle Autorisierungsentscheidungen (erlaubt und verweigert)
- Alle Konfigurationsänderungen
- Alle Admin-Operationen

**Log-Format:**
```json
{
  "timestamp": "2025-06-19T10:00:00.000Z",
  "level": "INFO",
  "event_type": "AUDIT",
  "action": "CREATE",
  "resource_type": "Event",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_sub": "user123",
  "user_roles": ["DISTRICT_ADMIN"],
  "district_id": "123e4567-e89b-12d3-a456-426614174000",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "status": "success",
  "changes": {"title": "Neuer Gottesdienst"},
  "metadata": {}
}
```

### 6.3 Compliance-Checks

- [ ] Audit-Logging ist für alle schreibenden Operationen implementiert
- [ ] Audit-Logs sind unveränderlich gespeichert
- [ ] Audit-Logs enthalten alle erforderlichen Felder
- [ ] Log-Retention Policy ist definiert und wird eingehalten

---

## 7. Betriebsregeln

### 7.1 Anforderungen

- ✅ **Secrets regelmaessig rotieren** (IDP-Admin, API-Keys, App-Secret).
- ✅ **Backup/Restore-Verfahren** regelmaessig testen.
- ✅ **Security-Incidents** dokumentieren und mit Massnahmen nachverfolgen.

### 7.2 Secrets Management

**Rotation Intervalle:**
- **IDP Admin Credentials:** Alle 90 Tage
- **API Keys:** Alle 90 Tage
- **Application Secrets (SECRET_KEY, etc.):** Alle 180 Tage
- **Database Credentials:** Alle 180 Tage
- **TLS Zertifikate:** Alle 90 Tage (oder automatisch via Let's Encrypt)

**Rotation Prozess:**
1. Neue Secrets generieren
2. Alte Secrets in allen Konfigurationen ersetzen
3. Services neu starten
4. Funktionstests durchführen
5. Alte Secrets sicher archivieren (30 Tage)
6. Alte Secrets endgültig löschen

### 7.3 Backup und Restore

**Backup-Strategie:**
- **Häufigkeit:** Täglich
- **Retention:** 30 Tage
- **Typ:** Vollständige Datenbank-Dumps (pg_dump -Fc)
- **Speicherort:** Externer, verschlüsselter Speicher
- **Test:** Monatlicher Restore-Test

**Restore-Prozess:**
1. Backup-Datei validieren
2. Testsystem vorbereiten
3. Backup wiederherstellen
4. Datenintegrität prüfen
5. Anwendungstests durchführen

### 7.4 Incident Response

**Incident Klassifikation:**
- **Kritisch:** Aktiver Angriff, Datenkompromittierung - Reaktionszeit: < 1 Stunde
- **Hoch:** Potenzielle Kompromittierung - Reaktionszeit: < 4 Stunden
- **Mittel:** Sicherheitsvorfall mit begrenzter Auswirkung - Reaktionszeit: < 24 Stunden
- **Niedrig:** Sicherheitsrelevantes Ereignis - Reaktionszeit: < 72 Stunden

**Response Team:**
- Security Team: security@nak-district-planner.example
- Projektleiter: project-lead@nak-district-planner.example
- Hosting Provider: support@hosting-provider.example

### 7.5 Compliance-Checks

- [ ] Secrets-Rotation Plan ist definiert
- [ ] Backup-Prozess ist dokumentiert und getestet
- [ ] Incident Response Procedure ist definiert
- [ ] Security Contacts sind aktuell

---

## 8. Docker Socket Self-Update

### 8.1 Sicherheitswarnung

- ⚠️ **NICHT** in Produktion ohne vorherige Sicherheitspruefung aktivieren.
- **UPDATE_MODE=docker-socket** mountet den Docker-Socket in den Backend-Container.
  Der Container erhaelt dadurch **root-equivalenten Zugriff** auf den Docker-Daemon.

### 8.2 Risikoanalyse

**Gefahren:**
- Container kann andere Container starten/stoppen
- Container kann auf Host-Dateisystem zugreifen
- Container kann Netzwerkverbindungen herstellen
- Container kann Docker-Daemon Konfiguration lesen/ändern

**Empfehlung:**
- **Produktion:** Immer **UPDATE_MODE=manual** verwenden
- **Entwicklung:** Docker-Socket Modus nur in isolierten Umgebungen
- **Alternative:** Externen Update-Service verwenden (z.B. Watchtower)

### 8.3 Implementierungsdetails

**Celery-Task `trigger_docker_update`:**
- Führt nur feste Befehle aus: `docker compose pull`, `docker compose up -d`
- Keine benutzerdefinierten Argumente
- Keine Shell-Command Injection möglich

**Sicherheitsmassnahmen:**
- Task ist nur für Superadmin zugänglich
- Task validiert die Befehle vor der Ausführung
- Task loggt alle Aktionen

### 8.4 Compliance-Checks

- [ ] UPDATE_MODE ist in Produktion auf "manual" gesetzt
- [ ] Docker-Socket ist in Produktion nicht gemountet
- [ ] Update-Prozess ist dokumentiert und getestet

---

## 9. Compliance Matrix

### 9.1 OWASP Top 10 2021

| OWASP | Kategorie | Status | Massnahmen |
|-------|----------|--------|------------|
| A01 | Broken Access Control | ⚠️ Teilweise | RBAC + Tenant-Isolation implementiert, RLS fehlt |
| A02 | Cryptographic Failures | ✅ Gut | Fernet Encryption, JWT Validation |
| A03 | Injection | ✅ Gut | SQLAlchemy ORM, Pydantic Validation |
| A04 | Insecure Design | ⚠️ Teilweise | Architektur gut, Features fehlen |
| A05 | Security Misconfiguration | ⚠️ Teilweise | Security Headers fehlen, Rate Limiting fehlt |
| A06 | Vulnerable Components | ✅ Gut | Automatisierte Scans |
| A07 | Identification and Auth Failures | ⚠️ Teilweise | OIDC gut, MFA fehlt |
| A08 | Software and Data Integrity | ✅ Gut | Hash-basierte Deduplizierung |
| A09 | Security Logging Failures | ❌ Kritisch | Audit-Logging fehlt |
| A10 | SSRF | ✅ Gut | Kein direktes URL-Fetching |

### 9.2 CIS Controls v8

| Control | Beschreibung | Status |
|---------|--------------|--------|
| 1.1 | Inventory of Hardware Assets | ✅ Gut |
| 1.2 | Inventory of Software Assets | ✅ Gut |
| 2.1 | Secure Config for Hardware | ⚠️ Teilweise |
| 2.2 | Secure Config for Software | ⚠️ Teilweise |
| 3.1 | Data Protection | ⚠️ Teilweise |
| 3.2 | Data Retention | ❌ Nicht implementiert |
| 4.1 | Secure Config Management | ⚠️ Teilweise |
| 5.1 | Account Management | ⚠️ Teilweise |
| 6.1 | Access Control | ⚠️ Teilweise |
| 7.1 | Vulnerability Management | ✅ Gut |
| 8.1 | Audit Log Management | ❌ Kritisch |

### 9.3 DSGVO / GDPR

| Anforderung | Status | Massnahmen |
|-------------|--------|------------|
| Datenminimierung | ✅ Gut | Nur notwendige Daten |
| Zweckbindung | ✅ Gut | Klare Datenverwendung |
| Löschkonzept | ❌ Nicht implementiert | Soft-Delete vorhanden |
| Betroffenenrechte | ❌ Nicht implementiert | Export/Löschung fehlt |
| Datenschutz-Folgenabschätzung | ❌ Nicht durchgeführt | - |

---

## 10. Priorisierte Massnahmen

### 10.1 Kritisch (SOFORT)

1. **Audit-Logging implementieren** (SEC-009)
   - Alle schreibenden Operationen loggen
   - Unveränderliche Speicherung
   - Log-Retention Policy definieren

2. **Rate Limiting für öffentliche Endpunkte** (SEC-016)
   - ICS-Export Endpunkte schützen
   - Redis-basierte Implementierung
   - Konfigurierbare Limits

### 10.2 Hoch (Q3 2025)

3. **CSRF-Schutz implementieren** (SEC-004)
   - Middleware für state-changing Requests
   - Token-basierte Validierung

4. **Tenant-Isolation verbessern** (SEC-021)
   - PostgreSQL RLS implementieren
   - Tenant-Context Middleware

### 10.3 Mittel (Q4 2025)

5. **API-Key Rotation** (SEC-002)
   - Automatisierte Rotation
   - Grace Period für alte Keys

6. **Security Headers** (A05)
   - CSP, HSTS, X-Frame-Options
   - X-Content-Type-Options, X-XSS-Protection

7. **DSGVO Compliance** (GDPR)
   - Löschkonzept implementieren
   - Betroffenenrechte umsetzen

### 10.4 Niedrig (2026)

8. **Multi-Factor Authentication** (A07)
   - OIDC Provider Integration
   - oder eigenständige TOTP-Implementierung

9. **Request Signing** (A04)
   - HMAC-Signing für Service-to-Service
   - oder Mutual TLS

---

## 11. Verweise

- [Detaillierte Security Analyse](docs/security-analysis.md)
- [Rollenmodell](docs/roles.md)
- [Approval Workflow](docs/approval-workflow.md)
- [Production Runbook](docs/production-runbook.md)
- [Security Workflow](.github/workflows/security.yml)

---

**Dokumentenverantwortlich:** Security Team  
**Nächste Review:** 2025-12-19  
**Klassifikation:** Intern - Nur für autorisiertes Personal
