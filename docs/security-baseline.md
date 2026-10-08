# Security Baseline

**Stand:** 4. Oktober 2026  
**Release-Ziel:** `1.0.0-rc.2`  
**Status:** aktiv; RC-2-Haertungen werden erst nach erfolgreichem Merge ihrer Workstreams als abgeschlossen markiert

Dieses Dokument beschreibt die verbindlichen Sicherheitsgrenzen des NAK District Planner. Detail- und Betriebsdokumente sind unter `docs/security/` und im `docs/production-runbook.md` verlinkt.

Legende: ✅ aktiv auf `main` · 🟡 offener RC-2-Workstream / Release-Gate · ❌ offen

## 1. Authentifizierung und Token-Vertrauen

- OIDC Authorization Code Flow mit PKCE: ✅
- JWT-Signaturpruefung ueber JWKS: ✅
- Issuer-, Audience-/`azp`- und Expiry-Pruefung: ✅
- Ungueltige JWTs duerfen **nicht** auf UserInfo/Introspection ausweichen: ✅ (PR #438)
- Opaque Access Tokens duerfen kontrolliert ueber UserInfo/Introspection validiert werden: ✅ (PR #438)
- Opaque-Token-Ergebnisse muessen fuer den konfigurierten Client/Issuer geeignet sein: ✅ (PR #438)

### 1.1 Fail-closed-Regel fuer JWTs

Ein Token, das syntaktisch wie ein JWT aufgebaut ist, wird ausschliesslich kryptographisch und gegen die erwarteten Claims validiert. Falsche Signatur, falscher Issuer/Audience, abgelaufene Tokens oder fehlende Pflichtclaims fuehren zur Ablehnung. Ein nachgelagerter UserInfo-/Introspection-Aufruf darf einen solchen Fehler nicht in einen Erfolg umwandeln.

UserInfo/Introspection ist nur fuer Tokenformen vorgesehen, die nicht als JWT lokal validierbar sind.

## 2. Browser-Session und Credential-Speicherung

Die Provider-Refresh-Credential bleibt serverseitig; der Browser haelt nur kurzlebige Session-Daten im Memory (PR #442).

Anforderungen:

- Provider-Refresh-Token bleibt serverseitig in einem `Secure`, `HttpOnly`, `SameSite`-Cookie: ✅ (PR #442)
- Provider-Refresh-Token wird nie in JSON an Browser-JavaScript zurueckgegeben: ✅ (PR #442)
- Access-/ID-Token werden nur in Memory gehalten, nicht in `localStorage`: ✅ (PR #442)
- ein Reload kann die Memory-Session ueber die serverseitige Refresh-Session wiederherstellen: ✅ (PR #442)
- Logout widerruft die serverseitig gehaltene Refresh-Credential best-effort und loescht das Cookie immer lokal: ✅ (PR #442)
- state-changing Cookie-Endpunkte bleiben CSRF-geschuetzt: ✅ (PR #442)

Tabgebundene Koordinationsdaten duerfen `sessionStorage` verwenden, sofern sie keine Provider-Credential enthalten.

## 3. Autorisierung und Tenant Isolation

- Membership-basiertes RBAC mit District-/Congregation-Scopes: ✅
- automatisiertes Route-Inventar fuer Auth-/RBAC-Coverage: ✅
- PostgreSQL Row Level Security auf Tenant-Tabellen: ✅
- getrennte Runtime-DB-Rolle ohne `BYPASSRLS`: ✅
- System-Worker-Kontext ist explizit und begrenzt: ✅
- Tenant-Autorisierung darf nicht auf unverifiziert dekodierten JWT-Claims beruhen: ✅ (PR #443)
- fachliche Autorisierung erfolgt nach verifizierter Authentifizierung ueber Dependencies/RBAC; RLS bleibt letzte Datenbankgrenze: ✅ (PR #443)

Ein vom Client kontrollierter Claim oder Header ist niemals alleinige Berechtigungsquelle.

## 4. Superadmin-Bootstrap

Der Bootstrap ist owner-controlled: ✅

- `app_superadmin_config` ist Owner-State und fuer die Runtime-Rolle weder lesbar noch schreibbar.
- `grant_bootstrap_superadmin(TEXT)` ist eine eng begrenzte SECURITY-DEFINER-Funktion.
- Auf einer frischen leeren Installation wird ohne owner-provisionierten Subject **kein** erster Login automatisch Superadmin.
- `SUPERADMIN_SUB` sollte vor der Bootstrap-Migration auf den exakten OIDC-`sub` gesetzt werden; alternativ provisioniert der DB-Owner die Konfiguration.
- Auf bestehenden Installationen pinnt die Migration bei fehlendem `SUPERADMIN_SUB` deterministisch einen vorhandenen Superadmin bzw. den fruehesten Benutzer.

Details: `docs/production-runbook.md`.

## 5. CSRF, Rate Limiting und oeffentliche Endpunkte

- Double-Submit-CSRF-Schutz fuer state-changing Browser-Requests: ✅
- globale und pfadspezifische Rate Limits: ✅
- ICS-Export ist tokenbasiert oeffentlich und rate-limited: ✅
- OIDC Discovery/Token-Exchange sind bewusst oeffentlich und rate-limited: ✅
- OIDC-Token-Exchange und oeffentliche Selbstregistrierung behalten bei Valkey-Ausfall einen lokalen Fallback-Limiter: ✅ (PR #443)
- Rate-Limiter-Degradation wird geloggt/telemetriert: ✅; lokale Fallback-Nutzung ist Bestandteil des RC-2-Monitorings

### 5.1 Oeffentliche Endpunkte

Eine Route darf nur dann ohne Bearer-Authentifizierung erreichbar sein, wenn sie im automatisierten `PUBLIC_ENDPOINTS`-Inventar dokumentiert ist. Ein neuer unauthentifizierter Endpunkt ohne explizite Klassifizierung muss CI brechen.

## 6. Daten- und Geheimnisschutz

- Secrets, API-Keys und Client-Credentials werden nicht committed.
- externe Kalender-Credentials werden verschluesselt gespeichert.
- sensitive Token-/Secret-Werte duerfen nicht in Logs oder Fehlerantworten gelangen.
- Production-Secrets werden ueber Secret-Management bereitgestellt.
- `SECRET_KEY`-Rotation ist ein geplanter Betriebsvorgang, weil davon verschluesselte Daten betroffen sein koennen.

| Datenklasse | Schutzbedarf | Mindestmassnahmen |
|---|---|---|
| Secrets / Provider-Credentials | kritisch | Secret-Management, keine Logs, keine Browser-Persistenz |
| Access-/ID-Tokens | hoch | HTTPS, kurze Lebensdauer, memory-only (PR #442) |
| Benutzer-/Membership-Daten | hoch | RBAC, RLS, Audit |
| Kalender-/Planungsdaten | mittel | Tenant-Isolation, RBAC, RLS |
| Logs/Metriken | mittel | keine Secrets, begrenzte Metadaten, Retention |

## 7. Transport- und Deployment-Grenzen

- Produktion nur hinter TLS-Termination: ✅
- Datenbank und Valkey/Redis nicht oeffentlich exponiert: ✅
- Anwendungseinstieg darf den vorgesehenen TLS-Proxy nicht ueber einen oeffentlichen Host-Port umgehen: ✅ (PR #440)
- CSP und Security Header sind restriktiv; externe `connect-src`-Ziele muessen begruendet sein: ✅ (PR #440)
- Runtime und Migration verwenden getrennte DB-Verantwortlichkeiten: ✅
- Schema-Migration gehoert in den Deployment-Schritt, nicht in den API-Lifespan: ✅ (PR #441)
- Ausgehende Kalender-Abrufe (ICS/CalDAV) sind SSRF-gehaertet: nur HTTPS, nur oeffentliche Zieladressen (Pruefung und IP-Pinning je Anfrage), keine Redirects, max. 10 MB, hoechstens 30 Sekunden je Abruf inkl. Retries, generische Fehlermeldungen: ✅ (#463)

### 7.1 Keine In-App-Updates

Die Anwendung **fuehrt keine Deployment-Updates aus** (#469): kein Update-Endpoint, kein Update-Task, kein Docker-Socket-Modus. Der Docker-Socket darf nie in einen Container gemountet werden (root-aequivalenter Host-Zugriff). Die Anwendung zeigt Administratoren nur an, dass eine neuere Version existiert (`GET /api/v1/system/version`); Updates erfolgen ausschliesslich durch Betreiber nach `docs/production-runbook.md`.

## 8. Audit und Nachvollziehbarkeit

- AuditMiddleware fuer relevante Requests: ✅
- Domain-/DB-Audit fuer kritische Writes: ✅
- verweigerte Tenant-/RBAC-Zugriffe werden nachvollziehbar erfasst: ✅
- Secrets und komplette Token-Claims duerfen nicht geloggt werden: verbindlich

Audit-Logs sind Sicherheitsdaten und muessen gegen unautorisierte Veraenderung sowie unbegrenzte Aufbewahrung geschuetzt werden.

## 9. Supply Chain und CI

Verpflichtende Sicherheits-/Qualitaetskontrollen im aktiven `main`-Ruleset:

- Backend Unit Tests & Coverage
- Frontend Unit Tests
- Frontend E2E
- Migration Graph & FK Names
- Encrypted Backup & Isolated Restore
- MegaLinter
- Dependency Review
- pip-audit
- bun audit
- CodeQL Python
- CodeQL JavaScript/TypeScript
- Backend-/Frontend-Image-Build
- Dokumentations-Build

Das Ruleset arbeitet strict und ohne Bypass. Aktuell werden noch keine Approvals verlangt; mindestens eine menschliche Approval plus stale-review/thread-resolution-Haertung bleibt Governance-Arbeit vor finalem 1.0.0.

## 10. Coverage und Testqualitaet

- Backend-Coverage-Gate: mindestens 80 Prozent: ✅
- Frontend-Coverage muss alle relevanten Production-Sources messen und fuer Statements, Branches, Functions und Lines mindestens 80 Prozent erreichen: ✅ (PR #439)
- Production-Code darf nicht breit ausgeschlossen werden, nur um ein Coverage-Gate zu erreichen.
- Security-Fixes muessen Negativ-/Ausnahmefaelle testen (invalid JWT, falscher Issuer/Audience, fehlender Refresh-Cookie, Provider-Fehler, Valkey-Ausfall, Cross-Tenant-Zugriff).
- RuntimeWarnings durch falsch gemockte/unawaited Coroutines gelten als Testqualitaets-Schuld und muessen vor finalem 1.0.0 bereinigt werden.

## 11. Release-Gate fuer RC-2

RC-2 ist erst freigabefaehig, wenn:

1. PR #438, #440, #441, #442 und #443 inhaltlich verifiziert und alle verpflichtenden Checks gruen sind;
2. PR #439 die reale Frontend-Coverage >80 Prozent erreicht;
3. keine blockierenden Security-/CodeQL-/Dependency-Findings offen sind;
4. Migration und Restore-Drill erfolgreich sind;
5. OpenSpec fuer die ausgelieferten Grenzen verifiziert und erledigte Changes archiviert sind;
6. Runbook und Architekturstatus dem ausgelieferten Code entsprechen.

## 12. Referenzen

- `docs/production-runbook.md`
- `docs/architecture-status.md`
- `docs/rbac-coverage.md`
- `docs/security/tenant-isolation.md`
- `docs/security/rate-limiting.md`
- `docs/security/csrf-protection.md`
- `.github/workflows/security.yml`
- `openspec/security-roadmap.md`
