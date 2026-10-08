## Why

Im dokumentierten Setup (externer TLS-Proxy -> `127.0.0.1:80` -> frontend-nginx -> backend) setzt nginx `X-Real-IP $remote_addr` ohne `set_real_ip_from`. Damit ist die IP immer die des Proxys bzw. Docker-Gateways: Alle anonymen Anfragen teilen einen Rate-Limit-Bucket, und ein einzelner Client mit >10 req/s auf `/api/v1/auth/oidc/token` oder `/api/v1/auth/me` erzeugt 429 fuer alle. Gleichzeitig protokolliert das Audit-Log den ersten (clientkontrollierten) `X-Forwarded-For`-Eintrag, wodurch die Audit-IP faelschbar ist (Issue #462).

## What Changes

- frontend-nginx stellt die Client-IP per `real_ip_header X-Forwarded-For; real_ip_recursive on;` wieder her, vertraut aber nur Peers aus `NGINX_REAL_IP_FROM` (Default `127.0.0.1/32 172.16.0.0/12`, generiert durch `/docker-entrypoint.d/15-real-ip-from.sh`).
- nginx reicht an das Backend nur `X-Real-IP` und ein bereinigtes `X-Forwarded-For` (beide `$remote_addr`) sowie `X-Forwarded-Proto` des Upstreams (Fallback `$scheme`) weiter.
- Backend: eine gemeinsame Funktion `get_client_ip()` fuer Rate Limiting und Audit. `X-Real-IP` gilt nur, wenn der TCP-Peer in `TRUSTED_PROXIES` liegt (Default Loopback + `172.16.0.0/12`); `X-Forwarded-For` wird nie ausgewertet.
- uvicorn laeuft mit `--no-proxy-headers`, um doppelte Header-Auswertung zu vermeiden.
- Runbook und `.env.example` dokumentieren `TRUSTED_PROXIES` und `NGINX_REAL_IP_FROM`.

## Capabilities

### New Capabilities
- `request-identity`: Vertrauenswuerdige Ermittlung der Client-IP fuer Rate Limiting und Audit hinter Reverse Proxies.

## Impact

- Rate-Limit-Buckets sind wieder pro Client statt installationsweit.
- Audit-IP ist nicht mehr per Header faelschbar.
- Betreiber, deren Proxy nginx nicht ueber Loopback/Docker-Bridge erreicht, muessen `NGINX_REAL_IP_FROM` ergaenzen.
