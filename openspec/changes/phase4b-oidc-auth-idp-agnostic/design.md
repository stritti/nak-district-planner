## Context

Phase 4a implementierte JWT-Authentifizierung via Keycloak-spezifischen Libraries (`python-jose`, `keycloak-js`). Damit die Architektur flexibel mehrere IDPs unterstützen kann — insbesondere Keycloak (VPS 5tritti.de) und Authentik (VPN) — müssen wir auf Standard-OIDC/OAuth2 migrieren.

**Current State:**
- Backend validiert JWT via Keycloak JWKS-Fetch
- Frontend nutzt `keycloak-js` Library
- ENV-Vars sind Keycloak-spezifisch (`KEYCLOAK_URL`, `KEYCLOAK_REALM`)
- Deployment via `keycloak-deploy/` Stack

**Constraint:** Beide IDPs müssen identische OIDC-Konfiguration nutzen (discovery, client credentials, scopes). Code sollte nicht IDP-spezifisch sein.

## Goals / Non-Goals

**Goals:**
- Abstrahiere IDP-Implementierungsdetails hinter OIDC-Standard
- Ein Backend/Frontend-Code funktioniert mit Keycloak UND Authentik UND jedem anderen OIDC Provider
- Identische Token-Validierung (JWKS, signature, claims)
- Setup-Guides für beide IDPs (nicht doppelter Code, sondern Konfiguration)

**Non-Goals:**
- Nicht: OAuth2-Flow-Variationen (device flow, client credentials, etc.) — nur authorization code flow
- Nicht: Multiple IDPs gleichzeitig in einer Instanz (nicht Federation)
- Nicht: IDP-spezifische Features (Keycloak Realms, Authentik Flows, etc.)

## Decisions

### Decision 1: OIDC vs OAuth2 vs Keycloak-Adapter
**Options:**
1. Keycloak-Adapter (current Phase 4a)
2. Generic OIDC (authlib + standard libraries)
3. Auth0/Okta SDK

**Decision:** Generic OIDC mit `authlib`
**Rationale:** 
- Authlib ist OIDC 1.0 compliant, funktioniert mit jedem Provider
- Keycloak AND Authentik sind OIDC-konform → kein Provider-Code nötig
- Leichter zu testen (Mock OIDC Server statt Keycloak)
- Weniger Abhängigkeiten

### Decision 2: JWKS Caching Strategy
**Options:**
1. Cache im Memory (aktuelle Phase 4a)
2. Redis Cache (shared zwischen Replicas)
3. Fetch every request (slow, insecure)

**Decision:** Memory-Cache mit 1h TTL + optional Redis fallback
**Rationale:**
- 1h ist sicher (IDP kann Keys rotieren)
- Memory-Cache funktioniert für Single-Instance
- Redis optional für Load-Balancing später
- `authlib` hat JWKS-Caching eingebaut

### Decision 3: Frontend OIDC Library
**Options:**
1. `keycloak-js` (IDP-spezifisch)
2. `@vueuse/core` OIDC Hooks + standard OAuth2 flow
3. `vue3-google-login` style generic OIDC
4. Custom implementation

**Decision:** `@vueuse/core` + custom OIDC composable
**Rationale:**
- `keycloak-js` ist Keycloak-specific
- `@vueuse/core` hat keine OIDC, aber gute OAuth2 patterns
- Custom OIDC composable mit 100 Zeilen Code, nutzt discovery + standard endpoints
- Testbar, keine IDP-Abhängigkeit

### Decision 4: ENV-Vars Naming
**Options:**
1. `KEYCLOAK_*` (Provider-spezifisch)
2. `OIDC_*` (Provider-agnostisch)
3. `IDP_*` (zu vage)

**Decision:** `OIDC_*`
**Rationale:**
- Klar, dass OIDC Standard
- Kurz und mnemonisch
- Andere Systeme verwenden auch `OIDC_` (Supabase, etc.)

### Decision 5: User Auto-Creation
**Option A:** Nur Standard OIDC Claims (`sub`, `email`, `preferred_username`)
**Option B:** Provider-spezifische Claims mappen

**Decision:** Option A, Standard Claims nur
**Rationale:**
- Alle OIDC Provider geben `sub` + `email`
- Weniger Mapping-Code
- Konsistent zwischen IDPs

### Decision 6: Multiple IDPs in Production
**Scenario:** Später könnte NAK Planner auf beiden 5tritti.de (Keycloak) UND VPN (Authentik) laufen

**Decision:** Ein Deployment pro IDP, identischer Code
**Rationale:**
- Keine Federation-Komplexität jetzt
- Später: separate Deployments mit unterschiedlichen `OIDC_*` ENV-Vars
- Einfacher zu debuggen

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| OIDC Compliance Unterschiede zwischen Keycloak + Authentik | Beide getesten mit Phase 4b Testsuite, in docs festhalten |
| Token-Expiration ist jetzt IDP-abhängig | Standardisiere auf 5min access + 30min refresh (beiden unterstützen) |
| JWKS-Fetch als Single Point of Failure | Fallback auf gecachte Keys + Alert bei Fetch-Fehler |
| Frontend-Redirect zu unbekanntem IDP | Fehler bei Initialization, nicht silent fail |

**Trade-offs:**
- Weniger Features als IDP-Spezifische Impl (z.B. Keycloak Realms) aber mehr Flexibilität
- Custom OIDC-Code statt Library, aber leichter zu debuggen

## Migration Plan

**Phase 1 (This):** IDP-agnostische Impl, beide IDPs getestet
1. Neuer `OIDCAdapter` mit authlib
2. Frontend OIDC Composable
3. ENV-Vars umschalten
4. Phase 4a Keycloak-Tests → OIDC-Tests anpassen

**Phase 2 (Later):** Keycloak & Authentik parallel in Produktion
1. 5tritti.de: Deploy mit `OIDC_DISCOVERY_URL=https://auth.5tritti.de/realms/nak-planner/.well-known/openid-configuration`
2. VPN: Deploy mit `OIDC_DISCOVERY_URL=https://authentik.internal/application/o/nak-planner/.well-known/openid-configuration`
3. Identischer Code, unterschiedliche Konfiguration

**Rollback:** Alte Phase 4a noch vorhanden, können zur Not zurück, aber kein Plan dafür (Keycloak-spezifisch)

## Open Questions

1. Welche Scopes sollte die OIDC Application anfordern? (`openid`, `profile`, `email` minimal)
2. Token-Lebensdauer: Aktuell Keycloak 5min access, 30min refresh — beide IDPs identisch?
3. Sollen wir PKCE enforcement für SPA auch aktivieren? (Modern best practice, aber komplexer)
