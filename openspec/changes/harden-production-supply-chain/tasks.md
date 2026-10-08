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

## 4. Advisory-Remediation (#456)

- [x] 4.1 `source-map-js` 1.2.1 → 1.2.2 (GHSA-68fv-2mgg-jv7q) in `services/frontend/bun.lock`, `bun.lock` und dem inzwischen entfernten `docs/bun.lock` gezielt aktualisiert; keine weiteren Pakete veraendert.
- [x] 4.2 Frozen Install, Frontend-Tests (377), Build und `bun audit` (Frontend: keine Befunde) mit Bun 1.2.23 verifiziert.
- [ ] 4.3 Docs-Toolchain (`vitepress` 1.x → vite 5/postcss/nanoid/js-yaml) separat behandeln: nur Build-Zeit, nicht im ausgelieferten Image; eigenes Issue.

## 5. Toolchain-Angleichung (#473)

- [x] 5.1 Runtime-Images auf Python 3.14.7 (#448) und Bun 1.4.2 (#446); CI-Pins (`ci.yml`, `alembic-check.yml`, `security.yml`, `docs.yml`) identisch.
- [x] 5.2 `requires-python >=3.14`, ruff `target-version = "py314"`, `uv.lock` neu gelockt.
- [x] 5.3 Unbenutzte `docs/package.json`/`docs/bun.lock` entfernt; Dependabot fuer Root-Compose und Root-Bun-Toolchain.
- [x] 5.4 Lokal mit Python 3.14.7/Bun 1.4.2 verifiziert: Backend-Unit (1231), Integration+Performance (160), Frontend frozen install, Lint, Tests (377), Build.
