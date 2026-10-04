## Why

Der RC-1 baut Container teilweise mit breiten oder `latest`-Tags und installiert Frontend-Abhaengigkeiten im Image ohne Lockfile-Zwang. Ausserdem wird der interne HTTP-nginx standardmaessig auf allen Host-Interfaces publiziert und kann dadurch einen vorgelagerten TLS-Reverse-Proxy umgehen.

## What Changes

- Python-, uv- und Bun-Buildtoolchain werden auf die in CI verwendeten Versionen festgelegt.
- Frontend-Image nutzt `bun install --frozen-lockfile`.
- PostgreSQL und Valkey werden auf konkrete getestete Patch-Versionen festgelegt.
- Der interne Frontend-nginx wird standardmaessig nur an Loopback gebunden.
- CSP, Referrer-Policy und Permissions-Policy werden am internen nginx gesetzt; HSTS bleibt Aufgabe der oeffentlichen TLS-Grenze.

## Capabilities

### Modified Capabilities
- `production-deployment`: Reproduzierbare Container-Builds und eindeutige TLS-Grenze.
- `security-baseline`: Browser-Security-Header und kein unbeabsichtigter HTTP-Bypass.

## Impact

- Lokaler Zugriff erfolgt standardmaessig ueber `127.0.0.1:8080` oder den externen Reverse Proxy.
- Abhaengigkeitsupdates erfordern bewusste Versionsanpassungen statt impliziter Tag-Updates.