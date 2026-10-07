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
