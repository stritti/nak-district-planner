## Why

RC-1 liest vor der eigentlichen OIDC-Validierung ein `sub` aus einem unvalidierten Bearer-JWT und verwendet diesen Claim fuer eine fruehe Membership-Pruefung. Dadurch koennen unterschiedliche 401/403-Pfade als Membership-Orakel wirken. Gleichzeitig arbeitet das Valkey-basierte Rate Limiting bei Infrastrukturfehlern bewusst fail-open, wodurch gerade oeffentliche Auth- und Registrierungsendpunkte ihren Abuse-Schutz verlieren.

## What Changes

- Tenant-Middleware interpretiert Bearer-Tokens nicht mehr selbst.
- Benutzeridentitaet fuer Tenant-Pruefungen stammt ausschliesslich aus einem bereits verifizierten Principal in `request.state.user`.
- Wenn ASGI-Middleware noch keinen verifizierten Principal besitzt, delegiert sie Autorisierung an FastAPI-RBAC und PostgreSQL-RLS.
- Die Rate-Limit-Middleware behandelt die blosse Anwesenheit eines Bearer-Headers nicht als authentifiziert.
- Bei Valkey-Fail-Open greift fuer OIDC Token Exchange und oeffentliche Selbstregistrierung ein kleiner, speicherbegrenzter lokaler Sliding-Window-Limiter.
- Normale Business-Endpunkte behalten die dokumentierte Availability-first Fail-Open-Strategie.

## Capabilities

### Modified Capabilities
- `tenant-isolation`: Identitaetsbasierte Tenant-Pruefungen verwenden nur verifizierte Principals.
- `rate-limiting`: Security-sensitive oeffentliche Endpunkte behalten auch bei Valkey-Ausfall einen begrenzten lokalen Abuse-Schutz.

## Impact

- Kein fruehes Membership-Orakel ueber gefaelschte JWT-Subjects.
- Der lokale Fallback ist absichtlich pro Prozess und ersetzt nicht den verteilten Valkey-Limiter.