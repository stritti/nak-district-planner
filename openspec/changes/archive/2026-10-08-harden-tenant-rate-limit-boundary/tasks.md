## 1. Tenant-Grenze

- [x] 1.1 Unvalidierte Bearer-Payloads nicht mehr in TenantMiddleware dekodieren.
- [x] 1.2 Wirkungslose TenantValidationMiddleware aus dem Runtime-Pfad entfernen.
- [x] 1.3 Tenant-Autorisierung bei verifizierten FastAPI-RBAC-Checks und PostgreSQL-RLS belassen.
- [x] 1.4 Authorization-Header allein nicht als authentifiziert fuer Rate-Limit-Multiplikator behandeln.

## 2. Rate-Limit-Fallback

- [x] 2.1 Speicherbegrenzten lokalen Sliding-Window-Limiter implementieren.
- [x] 2.2 Sensitive Endpunkte deklarativ statt ueber String-Arithmetik erkennen.
- [x] 2.3 Fallback-Grenzwerte als benannte Konfiguration fuehren.
- [x] 2.4 OIDC Token Exchange bei Valkey-Fail-Open lokal begrenzen.
- [x] 2.5 Oeffentliche Selbstregistrierung bei Valkey-Fail-Open lokal strenger begrenzen.
- [x] 2.6 Globale Bucket-Bereinigung amortisiert ausfuehren.
- [x] 2.7 Normale Business-Endpunkte weiterhin fail-open behandeln.
- [x] 2.8 Fallback-Buckets pro Regel statt pro Rohpfad fuehren (kein Eviction-Bypass ueber zufaellige District-UUIDs).
- [x] 2.9 Abgelehnte Requests nicht speichern; Bucket-Groesse bleibt <= Limit.
- [x] 2.10 Per-Prozess-Semantik (Limit x Prozesse x Replikas, Reset bei Neustart) in Spec und Runbook dokumentieren.

## 3. Tests

- [x] 3.1 Gefaelschtes Bearer-`sub` wird nicht in Tenant-Kontext uebernommen.
- [x] 3.2 Bearer-Header allein erhaelt keinen Auth-Multiplikator.
- [x] 3.3 Sensitive Route-Registry grenzt Admin-/ungueltige Pfade aus.
- [x] 3.4 Token-Exchange wird nach lokalem Limit mit 429 blockiert.
- [x] 3.5 Selbstregistrierung wird nach lokalem Limit mit 429 blockiert.
- [x] 3.6 Normaler Business-Endpunkt bleibt bei Redis-Ausfall verfuegbar.
- [x] 3.7 Lokaler Limiter bleibt speicherbegrenzt und bereinigt amortisiert.
- [x] 3.8 Tenant-Integrationstests erwarten keine unvalidierten `claimed_sub`-Metadaten; toter `claimed_sub`-Audit-Helfer entfernt.
- [x] 3.9 Regressionstests: Eviction-Bypass, Single-Key-Flood, nur Burst-Check fail-open, Trennung nach Identifier.
- [x] 3.10 Leader-Routen pruefen die Rolle vor dem Laden fremder Zeilen (403 statt 404, ACCESS_DENIED-Audit).

## 4. Verifikation

- [x] 4.1 Backend Unit-/Integrationstests erfolgreich.
- [x] 4.2 Backend Coverage >80 Prozent.
- [x] 4.3 CodeQL und Security Scans erfolgreich.
