# Umfassender Entwickler-Leitfaden

Dieser Leitfaden bietet detaillierte Anleitungen für Entwickler, die am NAK District Planner arbeiten möchten. Er umfasst Installation, Einrichtung der Entwicklungsumgebung, Ausführung von Tests und wichtige Security-Aspekte.

## Voraussetzungen

Bevor Sie mit der Entwicklung beginnen, stellen Sie sicher, dass folgende Tools installiert sind:

- **Docker** (Version 24+)
- **Docker Compose** (v2 Plugin, nicht Standalone)
- **Python** (3.11+ für lokale Alembic-Migrationen außerhalb Docker)
- **bun** (1.x für lokale Frontend-Entwicklung außerhalb Docker)
- **Git**

## 1. Projekt-Setup

### 1.1 Repository klonen
```bash
git clone <repository-url>
cd nak-district-planner
```

### 1.2 Umgebungskopie erstellen
```bash
cp .env.example .env
```

### 1.3 .env Datei konfigurieren
Öffnen Sie die `.env` Datei und ersetzen Sie die Platzhalter:

```dotenv
# PostgreSQL
POSTGRES_USER=nak
POSTGRES_PASSWORD=<sicheres-passwort-hier-eintragen>
POSTGRES_DB=nak_planner

# SQLAlchemy async connection string
# Für lokale Entwicklung (uv run uvicorn) auf localhost zeigen
DATABASE_URL=postgresql+asyncpg://nak:<passwort-hier-eintragen>@localhost:5433/nak_planner
REDIS_URL=redis://localhost:6379/0

# Security - generieren Sie diese Werte mit:
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Environment
APP_ENV=development

# OIDC Konfiguration (wird später für Auth benötigt)
OIDC_DISCOVERY_URL=https://oidc.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_SCOPES=openid profile email
VITE_OIDC_DISCOVERY_URL=https://oidc.example.com/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=your-client-id
```

> **Wichtig**: Für die lokale Entwicklung müssen `DATABASE_URL` und `REDIS_URL` auf `localhost` zeigen, da die Docker Compose Overrides diese im Container auf die internen Hostnamen (`db`, `redis`) setzen.

## 2. Entwicklungsumgebung starten

### 2.1 Vollständigen Stack mit Docker Compose starten
```bash
docker compose up -d
```

Der `docker-compose.override.yml` wird automatisch zusammengeführt und fügt Entwickler-Features hinzu:
- Hot-Reload für Backend und Worker
- Volume-Mounts für sofortiges Spiegeln von Code-Änderungen
- Exponierte Ports für direkten Zugriff

### 2.2 Dienststatus überprüfen
```bash
docker compose ps
```

Erwarteter Output:
```bash
NAME                          COMMAND                  SERVICE             STATE             
nak-district-planner-backend-1   "uv run uvicorn app..."   backend             running           
nak-district-planner-frontend-1  "/docker-entrypoint.…"   frontend            running           
nak-district-planner-worker-1    "uv run celery -A app..." worker              running           
nak-district-planner-db-1        "docker-entrypoint.s…"   db                  running           
nak-district-planner-redis-1     "docker-entrypoint.s…"   redis               running           
```

### 2.3 Logs überwachen
```bash
# Backend-Logs in Echtzeit verfolgen
docker compose logs -f backend

# Worker-Logs
docker compose logs -f worker

# Frontend-Logs (nginx)
docker compose logs -f frontend
```

## 3. Datenbank-Setup

### 3.1 Migrationen ausführen
Beim ersten Start und nach jeder neuen Migrationsdatei:
```bash
docker compose run --no-deps --rm backend alembic upgrade head
```

### 3.2 Neue Migration erstellen
Nach ORM-Änderungen:
```bash
docker compose run --no-deps --rm backend alembic revision --autogenerate -m "kurze beschreibung"
```

> Die Migrationsdatei wird unter `services/backend/alembic/versions/` erzeugt. Prüfen Sie sie stets vor dem Commit.

### 3.3 Testdaten seeden (optional)
```bash
make seed          # Persistente Testdaten einfügen
make seed-dry-run  # Nur anzeigen, was eingefügt würde
```

## 4. Lokale Entwicklung (ohne Docker für bestimmte Services)

Für schnellere Iterationszyklen können Backend oder Frontend lokal außerhalb Docker ausgeführt werden, während Datenbank und Redis weiterhin in Docker laufen.

### 4.1 Nur Datenbank und Redis starten
```bash
docker compose up -d db redis
```

### 4.2 Backend lokal entwickeln
```bash
cd services/backend
uv sync                              # Abhängigkeiten installieren
uv run alembic upgrade head          # Migrationen anwenden
uv run uvicorn app.main:app --reload # http://localhost:8000
```

### 4.3 Frontend lokal entwickeln
```bash
cd services/frontend
bun install                          # Abhängigkeiten installieren
bun run dev                          # http://localhost:5173 (proxied /api → localhost:8000)
bun run lint                         # ESLint ausführen
```

## 5. Testing

### 5.1 Backend-Tests
```bash
# Alle Tests
docker compose run --no-deps --rm backend pytest

# Unit-Tests only (schnell, kein DB/Network)
docker compose run --no-deps --rm backend pytest tests/unit/ -v

# Integration-Tests (benötigt laufende DB)
# Tipp: Nutze 'db-test' für persistente Testdaten: docker compose up -d db-test
# Dann: DATABASE_URL=postgresql+asyncpg://nak:changeme@localhost:5434/nak_planner_test pytest ...
docker compose run --no-deps --rm backend pytest tests/integration/ -v

# Mit Coverage-Bericht
docker compose run --no-deps --rm backend pytest --cov=app --cov-report=term-missing
```

### 5.2 Frontend-Tests
```bash
cd services/frontend
bun install
bun run test          # Vitest Tests
bun run test:watch    # Watch-Modus
```

## 6. Wichtige Entwicklungstools und Befehle

### 6.1 Makefile Befehle
Im Projektroot verfügbare Befehle:
```bash
make help           # Zeigt alle verfügbaren Befehle an
make migrate        # Datenbank-Migrationen ausführen
make seed           # Testdaten seeden
make seed-dry-run   # Testdaten anzeigen (ohne Änderungen)
make backend-test   # Backend-Tests ausführen
make frontend-test  # Frontend-Tests ausführen
make lint           # Linting für beide Anwendungen
```

### 6.2 Backend-Spezifische Werkzeuge
- **uv**: Paket-Manager für schnelle Dependency-Installation
- **alembic**: Datenbank-Migrationstool
- **pytest**: Testframework

### 6.3 Frontend-Spezifische Werkzeuge
- **bun**: Schneller JavaScript/TypeScript-Paket-Manager
- **vite**: Build-Tool und Dev-Server
- **vitest**: Testframework
- **eslint**: Linter

## 7. Security-Aspekte für Entwickler

### 7.1 Geheimnisse und sensible Daten
- **NIEMALS** echte Secrets, API Keys oder Passwörter im Repository committen
- Alle sensitiven Werte gehören in die `.env` Datei (gitignored) oder werden über Secret-Management-Systeme bereitgestellt
- Für Entwicklung können Platzhalterwerte verwendet werden, aber Produktionswerte müssen streng geschützt sein
- Beispiel für sichere Geheimnisgenerierung:
  ```bash
  # 32-Byte hex für SECRET_KEY und API_KEY
  python -c "import secrets; print(secrets.token_hex(32))"
  
  # Base64 für andere Anwendungsfälle
  openssl rand -base64 32
  ```

**Wichtig:**
- Überprüfen Sie vor jedem Commit mit `git diff`, dass keine Secrets enthalten sind
- Nutzen Sie Tools wie `git-secrets` oder `talisman` zur Prävention
- In CI/CD-Pipelines: Secrets immer als Environment-Variablen oder über Secret-Manager injizieren

### 7.2 Authentifizierung und Autorisierung

Das System verwendet OIDC (OpenID Connect) mit PKCE für sichere Authentifizierung:
- **Frontend**: Nutzt Authorization Code Flow mit PKCE über das `useOIDC` composable
- **Backend**: Validiert JWT-Tokens via JWKS, inkl. Issuer-/Audience-/Expiry-Prüfung
- **Rollenbasierte Zugriffskontrolle**: Siehe `docs/roles.md` für die detaillierte Rollenmatrix
- **Membership-Prüfung**: Geschützte Endpunkte erfordern gültige Bezirks-/Gemeinde-Mitgliedschaft (siehe `docs/approval-workflow.md`)

**Implementierungsmuster:**
```python
# Immer Berechtigungen prüfen BEVOR Operationen ausgeführt werden
from app.adapters.auth.permissions import assert_has_role_in_district, PermissionError
from app.domain.models.role import Role

# Für District-Operationen
try:
    assert_has_role_in_district(auth_context, Role.DISTRICT_ADMIN, district_id)
except PermissionError as e:
    raise HTTPException(status_code=403, detail=str(e))

# Für Congregation-Operationen
from app.adapters.auth.permissions import assert_has_role_in_congregation

try:
    assert_has_role_in_congregation(auth_context, Role.CONGREGATION_ADMIN, congregation_id)
except PermissionError as e:
    raise HTTPException(status_code=403, detail=str(e))
```

**Häufige Fehler:**
- ❌ Berechtigungsprüfung nach der Operation (zu spät!)
- ❌ Nur District-Admin prüfen, aber nicht die Zugehörigkeit zum spezifischen District
- ❌ Superadmin-Check vergessen für systemweite Operationen

### 7.3 Datenverschlüsselung

- **API-Keys und Client-Secrets**: Werden auf Ebene der Anwendungsschicht verschlüsselt bevor sie in die Datenbank geschrieben werden (Service-Layer-Decorator-Pattern)
- **Externe Kalender-Credentials**: OAuth-Tokens und andere Zugangsdaten für Kalenderintegrationen werden ebenfalls verschlüsselt gespeichert
- **Transportverschlüsselung**: In Produktion muss stets HTTPS verwendet werden (TLS-Termination am Reverse Proxy empfohlen)

**Verwendungsmuster:**
```python
# Immer Verschlüsselung für Credentials verwenden
from app.application.crypto import encrypt_credentials, decrypt_credentials

# Vor dem Speichern in der Datenbank
credentials = {"access_token": "...", "refresh_token": "...", "url": "..."}
encrypted = encrypt_credentials(credentials)
# encrypted in DB speichern

# Beim Auslesen
credentials = decrypt_credentials(encrypted_credentials_from_db)
```

**Wichtig:**
- Die Verschlüsselung verwendet Fernet (AES-128-CBC) mit einem von `SECRET_KEY` abgeleiteten Schlüssel
- Ändern Sie `SECRET_KEY`, um alle verschlüsselten Daten unlesbar zu machen!
- Testen Sie die Verschlüsselung/Entschlüsselung immer mit den tatsächlichen Produktionswerten

### 7.4 Netzwerk- und Container-Security

- **Port-Exposition**: In der Entwicklung werden bestimmte Ports nach außen exponiert für Debugging-Zwecke (Backend: 8000, DB: `${POSTGRES_PORT:-5432}`, Redis: 6379)
  - In Produktion wird KEIN `docker-compose.override.yml` verwendet, wodurch diese Expositions entfernt werden
  - Datenbank und Redis sind dann NICHT direkt vom Host erreichbar
- **Interne Kommunikation**: Services kommunizieren über das Docker-Netzwerk mittels Service-Namen (`backend`, `db`, `redis`)
- **CORS**: Sollte restriktiv konfiguriert sein - in Entwicklung oft locker für lokales Testen, in Produktion auf spezifische Domains beschränkt

**Produktionskonfiguration:**
```yaml
# docker-compose.yml (Produktion) - KEINE exponierten Ports
services:
  backend:
    ports: []  # Nicht nach außen exponiert
    # ...
  db:
    ports: []  # Nicht nach außen exponiert
    # ...
  redis:
    ports: []  # Nicht nach außen exponiert
```

**Sicherheitswarnung:**
- Exponieren Sie NIEMALS Datenbank-Ports in Produktion
- Verwenden Sie NIEMALS `docker-compose.override.yml` in Produktion
- Nutzen Sie Firewall-Regeln, um den Zugriff auf die Docker-Hosts zu beschränken

### 7.5 API-Security

- **Authentifizierung**: Geschützte Endpunkte erfordern entweder:
  - `X-API-Key` Header für Service-to-Service-Kommunikation
  - `Authorization: Bearer <jwt-token>` für Benutzer-Aktionen (nach OIDC-Login)
- **Rate Limiting**: Wird für öffentliche Endpunkte (wie ICS-Export) implementiert, um Missbrauch zu verhindern
- **Fehlerbehandlung**: Sicherheitsrelevante Fehler dürfen keine sensiblen Internas preisgeben (keine Stack Traces oder Systemdetails in Fehlerantworten)

**Fehlerbehandlungsmuster:**
```python
# In main.py - generischer Exception Handler
@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    # In Entwicklung: detaillierte Fehlermeldungen
    if settings.app_env == "development":
        detail = str(exc)
    # In Produktion: generische Fehlermeldung
    else:
        detail = "Internal Server Error"
    
    # Loggen für Debugging (ohne sensible Daten!)
    logger.error(f"Error: {exc}", exc_info=True)
    
    return JSONResponse(status_code=500, content={"detail": detail})
```

**Input-Validierungsmuster:**
```python
# Immer Pydantic v2 für Input-Validation verwenden
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid

class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    category: str | None = Field(default=None, max_length=50)
    
    @field_validator('end_at')
    @classmethod
    def validate_end_after_start(cls, v: datetime, values: dict) -> datetime:
        if 'start_at' in values and v <= values['start_at']:
            raise ValueError('end_at must be after start_at')
        return v
```

### 7.6 Dependency-Security

- Das Projekt nutzt automatisierte Security-Scans über GitHub Actions (siehe `.github/workflows/security.yml`)
  - **pip-audit** für Python-Abhängigkeiten
  - **bun audit** für JavaScript/TypeScript-Abhängigkeiten
  - **CodeQL** für allgemeine Schwachstellenanalyse
- Bei neuen Dependencies sollte immer eine kurze Risikoeinschätzung durchgeführt werden

**Dependency Review Prozess:**
1. Prüfen Sie die Package-Popularität und Wartung auf [pypi.org](https://pypi.org/) oder [npmjs.com](https://www.npmjs.com/)
2. Überprüfen Sie die Sicherheitshistorie auf [Snyk](https://snyk.io/) oder [GitHub Advisory Database](https://github.com/advisories)
3. Prüfen Sie die Lizenzkompatibilität
4. Dokumentieren Sie die Entscheidung im PR

**Lokale Scans:**
```bash
# Python Dependencies scannen
cd services/backend
uv export --format requirements-txt --no-dev --no-emit-project -o /tmp/requirements.txt
pip-audit -r /tmp/requirements.txt

# JavaScript Dependencies scannen
cd services/frontend
bun audit --level moderate

# CodeQL Analyse (erfordert Setup)
codeql database create --language python .
codeql analyze --format=sarif --output=results.sarif .
```

### 7.7 Betriebs-Security

- **Secrets-Rotation**: Regelmäßiges Rotieren von IDP-Administratorzugängen, API-Keys und Anwendungsschlüsseln
- **Backup-Verfahren**: Regelmäßige Tests des Backup/Wiederherstellungs-Verfahrens für PostgreSQL-Daten
- **Audit-Logs**: Obwohl noch nicht vollständig implementiert, sollen sicherheitsrelevante Aktionen auditierbar sein (Roadmap-Punkt)

**Backup- und Restore-Test:**
```bash
# Backup erstellen
docker exec nak-district-planner-db-1 \
  pg_dump -U nak -d nak_planner -Fc \
  > backup_$(date +%Y%m%d_%H%M%S).dump

# Backup testen (auf Testsystem)
docker exec -i nak-district-planner-db-test-1 \
  pg_restore -U nak -d nak_planner_test --clean < backup.dump

# Verify Backup-Integrität
pg_restore --list backup.dump | head -20  # Header prüfen
```

**Secrets-Rotation Checkliste:**
- [ ] Neue Secrets generieren
- [ ] Alte Secrets in allen Konfigurationen ersetzen
- [ ] Services neu starten
- [ ] Funktionstests durchführen
- [ ] Alte Secrets sicher archivieren (für Rollback)
- [ ] Nach 30 Tagen: Alte Secrets endgültig löschen

### 7.8 Security Testing

**Testkategorien:**

1. **Authentication Tests**
   - Testen Sie alle Auth-Flows (OIDC, API-Key)
   - Testen Sie Token-Ablauf und Refresh
   - Testen Sie ungültige Tokens

2. **Authorization Tests**
   - Testen Sie alle Rollenkombinationen
   - Testen Sie Cross-Tenant Zugriff (muss scheitern!)
   - Testen Sie Privilege Escalation Versuche

3. **Input Validation Tests**
   - Testen Sie SQL Injection Versuche
   - Testen Sie XSS Versuche
   - Testen Sie Buffer Overflow Versuche
   - Testen Sie Malformed JSON/XML

4. **Error Handling Tests**
   - Verifizieren Sie, dass keine Stack Traces in Produktion angezeigt werden
   - Verifizieren Sie, dass Fehlercodes konsistent sind

**Beispiel: Authorization Test**
```python
# Test: User mit VIEWER Rolle darf keine Events erstellen
def test_viewer_cannot_create_event():
    # Setup
    viewer_user = create_test_user(role=Role.VIEWER, district_id=test_district_id)
    client = TestClient(app)
    
    # Versuch, Event zu erstellen
    response = client.post(
        "/api/v1/events",
        json={
            "title": "Test Event",
            "start_at": "2025-01-01T10:00:00Z",
            "end_at": "2025-01-01T11:00:00Z",
            "district_id": str(test_district_id),
        },
        headers={"Authorization": f"Bearer {viewer_user.token}"},
    )
    
    # Verifizieren: 403 Forbidden
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]
```

### 7.9 Security Checklist für Code Reviews

**Vor dem Merge prüfen:**

- [ ] **Secrets:** Keine Passwörter, API-Keys, Tokens oder andere Secrets im Code
- [ ] **Input Validation:** Alle API-Endpunkte haben Pydantic-Validierung
- [ ] **Authorization:** Alle schreibenden Operationen haben Berechtigungsprüfungen
- [ ] **Tenant Isolation:** Kein Cross-Tenant Datenzugriff möglich
- [ ] **Data Encryption:** Sensible Daten werden verschlüsselt gespeichert
- [ ] **Error Handling:** Keine sensiblen Daten in Fehlermeldungen
- [ ] **Logging:** Keine sensiblen Daten in Logs
- [ ] **Dependencies:** Neue Abhängigkeiten wurden auf Sicherheitsrisiken geprüft
- [ ] **Tests:** Sicherheitsrelevante Änderungen haben entsprechende Tests
- [ ] **Dokumentation:** Sicherheitsrelevante Änderungen sind dokumentiert

### 7.10 Security Resources

**Interne Dokumentation:**
- `docs/security-baseline.md` - Sicherheits-Baseline und verbindliche Regeln
- `docs/security-analysis.md` - Umfassende Security-Analyse mit Threat Modeling
- `docs/roles.md` - Rollenmodell und Berechtigungsmatrix
- `docs/approval-workflow.md` - Benutzer-Onboarding und Freigabe-Workflow
- `docs/production-runbook.md` - Betriebs- und Incident-Grundabläufe

**Externe Ressourcen:**
- [OWASP Top 10](https://owasp.org/Top10/) - Top 10 Web Application Security Risks
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) - Application Security Verification Standard
- [CIS Controls](https://www.cisecurity.org/controls/) - Center for Internet Security Controls
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework) - NIST CSF
- [GitHub Security Lab](https://securitylab.github.com/) - Security Research und Tools

**Tools:**
- [Snyk](https://snyk.io/) - Vulnerability Management
- [Trivy](https://github.com/aquasecurity/trivy) - Container Security Scanner
- [Semgrep](https://semgrep.dev/) - Statische Code-Analyse
- [Burp Suite](https://portswigger.net/burp) - Web Application Security Testing

### 7.11 Security Incident Reporting

**Bei Verdacht auf Sicherheitsvorfall:**

1. **Nicht panisch reagieren**, aber schnell handeln
2. **System nicht neu starten** (könnte Beweise zerstören)
3. **Netzwerkverbindungen nicht trennen** (könnte Angreifer warnen)
4. **Sicherheitsteam kontaktieren:** <security@nak-district-planner.example>
5. **Alle Beobachtungen dokumentieren:**
   - Zeitstempel
   - Betroffene Systeme
   - Beobachtetes Verhalten
   - Verdächtige IPs oder Accounts
   - Getroffene Massnahmen

**Incident Klassifikation:**
- **Kritisch:** Aktiver Angriff, Datenkompromittierung - Reaktionszeit: < 1 Stunde
- **Hoch:** Potenzielle Kompromittierung - Reaktionszeit: < 4 Stunden
- **Mittel:** Sicherheitsvorfall mit begrenzter Auswirkung - Reaktionszeit: < 24 Stunden
- **Niedrig:** Sicherheitsrelevantes Ereignis - Reaktionszeit: < 72 Stunden

## 8. Deployment-Hinweise für Entwickler

### 8.1 Unterschied zwischen Entwicklung und Produktion
In der Produktion wird KEIN `docker-compose.override.yml` verwendet, was bedeutet:
- Keine Volume-Mounts für den Quellcode (Code liegt im Image)
- Kein `--reload` Flag; uvicorn läuft im stabilen Produktionsmodus
- Keine exponierten Ports für Backend (8000), DB (5432) oder Redis (6379) nach außen
- Alle Services laufen ohne Entwickler-Debugging-Tools

### 8.2 Produktions-Build erstellen
```bash
# Nur Produktions-Compose-File verwenden
docker compose -f docker-compose.yml build

# Production-Env vorbereiten (niemals Entwicklungswerte übernehmen!)
# .env für Produktion muss folgende Werte enthalten:
#   - Echte sichere Passwörter
#   - Korrekte interne Hostnamen (db, redis) in DATABASE_URL/REDIS_URL
#   - APP_ENV=production
docker compose -f docker-compose.yml up -d
```

### 8.3 Health-Check in Produktion
```bash
curl http://localhost/api/health
# Sollte {"status":"ok"} zurückgeben
```

## 9. Fehlersuche und Debugging

### 9.1 Häufige Probleme
- **"Port is already allocated"**: Ein anderer Dienst läuft bereits auf demselben Port
  - Lösung: Andere Dienste beenden oder andere Ports in compose-files verwenden
- **"database connection failed"**: Prüfen Sie ob der DB-Container läuft und die Zugangsdaten korrekt sind
- **"Hot-Reload funktioniert nicht"**: Stellen Sie sicher, dass Sie im richtigen Verzeichnis arbeiten und die Volume-Mounts aktiv sind
- **Frontend kann Backend nicht erreichen**: Prüfen Sie ob der Backend-Container läuft und ob das Proxying in Vite korrekt konfiguriert ist

### 9.2 Debugging-Tools
- **Backend**:
  - `--reload` Modus für automatischen Neustart bei Codeänderungen
  - Ausführliche Logs über `docker compose logs -f backend`
  - Direktzugriff auf Swagger UI: `http://localhost:8000/docs` (nur Entwicklung)
- **Frontend**:
  - Vite Dev Server mit Hot-Module-Replacement
  - Vue Devtools Browser-Erweiterung für Komponenteninspektion
  - API-Proxy-Konfiguration in `vite.config.ts`

### 9.3 Ressourcen überwachen
```bash
# Container-Ressourcenauslastung
docker stats

# Logs mit Timestamps und Details
docker compose logs --timestamps --tail=100 backend
```

## 10. Weiterführende Dokumentation

Für spezifischere Themen konsultieren Sie bitte:
- **Architektur**: `docs/architecture-status.md` und `openspec/architecture/overview.md`
- **Use Cases**: `docs/use-cases.md` (UC-01 bis UC-06)
- **Rollen und Berechtigungen**: `docs/roles.md`
- **Release-Prozess**: `docs/release-process.md`
- **Produktionsbetrieb**: `docs/production-runbook.md`
- **Security Details**: `docs/security-baseline.md`

Dieser Entwickler-Leitfaden wird regelmäßig aktualisiert. Bei Fragen oder Unklarheiten konsultieren Sie bitte das Engineering-Team oder prüfen Sie die genannten Referenzdokumente.
