## Why

Der RC-1 baut Container teilweise mit breiten oder `latest`-Tags und installiert Frontend-Abhaengigkeiten im Image ohne Lockfile-Zwang. Ausserdem wird der interne HTTP-nginx standardmaessig auf allen Host-Interfaces publiziert und kann dadurch einen vorgelagerten TLS-Reverse-Proxy umgehen.

## What Changes

- Die bestehende Python-3.11-Runtime-Linie wird auf eine konkrete Patch-Version festgelegt; ein Python-Major-/Minor-Upgrade ist bewusst nicht Teil dieses Changes.
- uv und Bun werden auf konkrete getestete Versionen festgelegt.
- Frontend-Image nutzt `bun install --frozen-lockfile`.
- PostgreSQL und Valkey werden auf konkrete getestete Patch-Versionen festgelegt.
- Dependabot ueberwacht die gepinnten Docker-Basis- und Tool-Images.
- Der interne Frontend-nginx wird standardmaessig nur an Loopback gebunden.
- CSP, Referrer-Policy und Permissions-Policy werden am internen nginx gesetzt; `connect-src` bleibt auf Same-Origin begrenzt und HSTS bleibt Aufgabe der oeffentlichen TLS-Grenze.

## Capabilities

### Modified Capabilities
- `production-deployment`: Reproduzierbare Container-Builds, Browser-Security-Header und eindeutige TLS-Grenze ohne unbeabsichtigten HTTP-Bypass.

## Impact

- Lokaler Zugriff bleibt ueber den dokumentierten Reverse-Proxy-Zielport `127.0.0.1:80` erreichbar, wird aber nicht mehr an oeffentliche Host-Interfaces gebunden.
- Abhaengigkeitsupdates werden ueber Dependabot sichtbar und bleiben explizite, reviewbare Versionsaenderungen.
- Ein spaeteres Python-3.13-Upgrade benoetigt einen separaten Change mit eigener Kompatibilitaetsverifikation.
