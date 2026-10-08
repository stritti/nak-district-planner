## Why

RC-1 liest vor der eigentlichen OIDC-Validierung ein `sub` aus einem unvalidierten Bearer-JWT und verwendet diesen Claim fuer eine fruehe Membership-Pruefung. Dadurch koennen unterschiedliche 401/403-Pfade als Membership-Orakel wirken. Gleichzeitig arbeitet das Valkey-basierte Rate Limiting bei Infrastrukturfehlern bewusst fail-open, wodurch gerade oeffentliche Auth- und Registrierungsendpunkte ihren Abuse-Schutz verlieren.

## What Changes

- Tenant-Middleware interpretiert Bearer-Tokens nicht mehr selbst und extrahiert nur nicht vertrauenswuerdige Routing-Kontexte wie District-/Congregation-IDs.
- Die bisherige `TenantValidationMiddleware` wird aus dem Runtime-Pfad entfernt, weil ASGI-Middleware vor den FastAPI-Authentifizierungsdependencies keinen verifizierten Principal besitzt.
- Tenant-Autorisierung bleibt bei verifizierten FastAPI-RBAC-Checks und PostgreSQL-RLS.
- Die Rate-Limit-Middleware behandelt die blosse Anwesenheit eines Bearer-Headers nicht als authentifiziert.
- Security-sensitive Fallback-Routen und deren Limits sind deklarativ konfiguriert statt ueber String-Arithmetik und Magic Numbers verteilt.
- Bei Valkey-Fail-Open greift fuer OIDC Token Exchange und oeffentliche Selbstregistrierung ein kleiner, speicherbegrenzter lokaler Sliding-Window-Limiter.
- Die globale Bucket-Bereinigung des lokalen Limiters wird amortisiert statt bei jeder Anfrage ausgefuehrt.
- Normale Business-Endpunkte behalten die dokumentierte Availability-first Fail-Open-Strategie.

## Capabilities

### Modified Capabilities
- `tenant-isolation`: Identitaetsbasierte Tenant-Autorisierung verwendet ausschliesslich verifizierte Principals in RBAC/RLS statt unvalidierter Middleware-Claims.
- `rate-limiting`: Security-sensitive oeffentliche Endpunkte behalten auch bei Valkey-Ausfall einen begrenzten lokalen Abuse-Schutz.

## Impact

- Kein fruehes Membership-Orakel ueber gefaelschte JWT-Subjects.
- Keine Middleware suggeriert Tenant-Autorisierung, die sie im normalen FastAPI-Ablauf nicht belastbar leisten kann.
- Der lokale Fallback ist absichtlich pro Prozess und ersetzt nicht den verteilten Valkey-Limiter.
