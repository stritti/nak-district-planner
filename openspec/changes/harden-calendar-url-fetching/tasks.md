## 1. Tests (rot)

- [x] 1.1 Negativtests für Loopback, 169.254.0.0/16, RFC1918, CGNAT, IPv6 ULA, `::1`, IPv4-mapped IPv6, NAT64, 6to4
- [x] 1.2 Tests für Redirect auf internes Ziel, Re-Validierung je Hop, übergroße Antwort (Content-Length und Stream)
- [x] 1.3 Tests für generische Fehlermeldungen ohne URL/Zugangsdaten/Statuscode
- [x] 1.4 API-Tests: unsichere URL bei Create/Update → 422
- [x] 1.5 Production-Guard-Test für `CALENDAR_ALLOW_INSECURE_URLS`

## 2. Umsetzung

- [x] 2.1 `url_guard.py` mit statischer Validierung, `GuardedTransport` (Resolve, Prüfen, IP-Pinning mit Host/SNI) und Größenlimit
- [x] 2.2 ICS-/CalDAV-Connector auf `guarded_client()` umstellen, Redirects deaktivieren
- [x] 2.3 Generische Fehlertexte in `http_policy.py`, CalDAV und `run_sync`
- [x] 2.4 Validierung im Router bei Create/Update
- [x] 2.5 Setting `CALENDAR_ALLOW_INSECURE_URLS` + `production_guard` + `.env.example`

## 3. Review-Nacharbeiten (Codex)

- [x] 3.1 Komprimierte Antworten ablehnen (`Accept-Encoding: identity`), damit das Größenlimit dekodierte Bytes zählt
- [x] 3.2 `CALENDAR_ALLOW_INSECURE_URLS` bereits beim Laden der Settings in Produktion ablehnen (API, Worker, Beat)
- [x] 3.3 Fallback über alle geprüften Adressen bei Verbindungsfehlern
- [x] 3.4 DNS-Auflösung durch Connect-Timeout begrenzen
- [x] 3.5 Reservierte und IPv4-translatable (`::ffff:0:0/96`) Adressen blockieren
- [x] 3.6 Blockierte DNS-Antwort mit gleicher Meldung wie nicht auflösbarer Host (kein DNS-Orakel)
- [x] 3.7 Hostnamen normalisieren (Kleinschreibung, abschließende Punkte), `localhost.` ablehnen
- [x] 3.8 `CALENDAR_NAT64_PREFIXES` (RFC 6052, /32–/96) mit Extraktion der eingebetteten IPv4; `64:ff9b:1::/48` ergänzt
- [x] 3.9 Legacy-IPv4-Literale (`127.1`, `2130706433`, `0x7f.1`) werden statisch als IPv4 interpretiert und abgelehnt (Codex-Review #487).
- [x] 3.10 IPv6 site-local (`fec0::/10`) explizit ablehnen; Python meldet den Bereich als `is_global` (Codex-Review #487).
- [x] 3.11 Eine gemeinsame Connect-Deadline für DNS-Auflösung und alle Adress-Fallbacks (Codex-Review #487).
