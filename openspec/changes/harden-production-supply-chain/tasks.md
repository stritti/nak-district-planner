## 1. Reproduzierbare Builds

- [x] 1.1 Backend-Python-Version auf die CI-Version pinnen.
- [x] 1.2 uv auf die CI-Version pinnen.
- [x] 1.3 Bun auf die CI-Version pinnen.
- [x] 1.4 Frontend-Abhaengigkeiten mit `--frozen-lockfile` installieren.
- [x] 1.5 PostgreSQL und Valkey auf getestete Patch-Versionen pinnen.

## 2. Deployment-Grenze

- [x] 2.1 Internen nginx standardmaessig nur an Loopback publizieren.
- [x] 2.2 CSP, Referrer-Policy und Permissions-Policy setzen.
- [x] 2.3 HSTS explizit an der externen TLS-Grenze belassen.

## 3. Verifikation

- [ ] 3.1 Docker-Builds fuer Backend und Frontend erfolgreich.
- [ ] 3.2 Compose-Konfiguration erfolgreich validiert.
- [ ] 3.3 Frontend-E2E unter CSP erfolgreich.