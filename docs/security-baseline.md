# Security Baseline

Dieses Dokument fasst die verbindlichen Sicherheitsleitplanken fuer Entwicklung und Betrieb zusammen.

## 1. Authentifizierung und Autorisierung

- OIDC (Authorization Code Flow mit PKCE) fuer Frontend-Login.
- Token-Validierung im Backend via JWKS, inkl. Issuer-/Audience-/Expiry-Pruefung.
- Rollen und Scopes gemaess `docs/roles.md`.
- Membership-Gate fuer geschuetzte Endpunkte gemaess `docs/approval-workflow.md`.

## 2. Daten- und Geheimnisschutz

- API-Keys, Client-Secrets und Zugangsdaten niemals im Repository speichern.
- Sensible Konfiguration nur ueber `.env` / Secret-Management.
- Externe Kalender-Credentials verschluesselt speichern (Service-Layer-Verschluesselung).

## 3. Transport- und Netzwerksicherheit

- Produktion nur ueber HTTPS (TLS-Termination am Reverse Proxy).
- Interne Dienste (DB, Redis, Backend-Port) nicht oeffentlich exponieren.
- CORS restriktiv konfigurieren.

## 4. API-Schutz

- Geschuetzte Endpunkte erfordern gueltige Authentifizierung.
- Oeffentliche Endpunkte (z. B. ICS-Export) erhalten Rate-Limiting
  (Roadmap: `introduce-non-functional-baseline`).
- Sicherheitsrelevante Fehler werden ohne sensitive Interna ausgeliefert.

## 5. Supply-Chain und statische Scans

- Security-Workflow nutzt CodeQL, pip-audit und bun audit
  (siehe `.github/workflows/security.yml`).
- PRs mit neuen Dependencies erfordern kurze Risikoeinschaetzung.

## 6. Audit und Nachvollziehbarkeit

- Governance-relevante Aktionen sollen auditierbar sein.
- Vollstaendige Audit-Log-Abdeckung ist als priorisierte Roadmap-Massnahme definiert.

## 7. Betriebsregeln

- Secrets regelmaessig rotieren (IDP-Admin, API-Keys, App-Secret).
- Backup/Restore-Verfahren regelmaessig testen.
- Security-Incidents dokumentieren und mit Massnahmen nachverfolgen.

## 8. Docker Socket Self-Update

- **NICHT** in Produktion ohne vorherige Sicherheitspruefung aktivieren.
- **UPDATE_MODE=docker-socket** mountet den Docker-Socket in den Backend-Container.
  Der Container erhaelt dadurch root-equivalenten Zugriff auf den Docker-Daemon.
- Empfohlener Modus fuer Produktion: **UPDATE_MODE=manual** — Admins fuehren die
  Update-Befehle manuell per SSH aus.
- Der docker-socket Modus ist ausschliesslich fuer vertrauenswuerdige Umgebungen
  (abgesicherte Server, keine Multi-Tenancy) geeignet.
- Der Celery-Task `trigger_docker_update` fuehrt nur fixe Befehle aus
  (`docker compose pull`, `docker compose up -d`). Es werden keine
  benutzer-eingegebenen Argumente an die Shell uebergeben.
