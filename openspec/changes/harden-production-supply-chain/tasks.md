## 1. Reproduzierbare Builds

- [x] 1.1 Bestehende Python-3.11-Runtime auf eine konkrete Patch-Version pinnen.
- [x] 1.2 uv auf eine konkrete getestete Version pinnen.
- [x] 1.3 Bun auf eine konkrete getestete Version pinnen.
- [x] 1.4 Frontend-Abhaengigkeiten mit `--frozen-lockfile` installieren.
- [x] 1.5 PostgreSQL und Valkey auf getestete Patch-Versionen pinnen.
- [x] 1.6 Gepinnte Docker-Basis- und Tool-Images durch Dependabot ueberwachen.

## 2. Deployment-Grenze

- [x] 2.1 Internen nginx standardmaessig nur an Loopback publizieren.
- [x] 2.2 CSP, Referrer-Policy und Permissions-Policy setzen.
- [x] 2.3 Browser-Verbindungen per CSP auf Same-Origin begrenzen.
- [x] 2.4 HSTS explizit an der externen TLS-Grenze belassen.

## 3. Verifikation

- [x] 3.1 Docker-Builds fuer Backend und Frontend erfolgreich.
- [x] 3.2 Compose-Konfiguration erfolgreich validiert.
- [x] 3.3 Frontend-E2E unter CSP erfolgreich.
