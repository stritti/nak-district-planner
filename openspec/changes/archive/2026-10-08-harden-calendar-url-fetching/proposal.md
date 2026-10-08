## Why

Issue #463: Kalender-URLs (`credentials.url` für ICS/CalDAV) wurden beim Anlegen/Ändern nicht validiert; schon `CONGREGATION_ADMIN` konnte beliebige Ziele eintragen. Der ICS-Client folgte Redirects, es gab keine Prüfung auf private/Loopback/Link-local/ULA-Netze, Antworten wurden unbegrenzt gelesen, und unterschiedliche Fehlertexte ("HTTP <code>" vs. "Transportfehler") wirkten über den Sync-Endpunkt und `last_sync_error` als Port-/Service-Orakel. CalDAV-Fehler enthielten zudem die URL inkl. eingebetteter Zugangsdaten. Damit war Server-Side Request Forgery gegen interne Dienste (DB, Valkey, Cloud-Metadaten) möglich.

## What Changes

- Neuer Adapter-Baustein `app/adapters/calendar/url_guard.py`:
  - `validate_calendar_url()` — statische Prüfung bei Create/Update (nur `https`, Host erforderlich, keine Zugangsdaten in der URL, IP-Literale und `localhost` nur wenn öffentlich). Verstöße → HTTP 422.
  - `GuardedTransport` — prüft **jede** Anfrage (auch jeden Redirect-Hop): Host einmal auflösen, alle Adressen müssen global routbar sein (IPv4-mapped, 6to4 und NAT64 werden entpackt), dann Verbindung zur geprüften IP mit unverändertem Host-Header und TLS-SNI (DNS-Rebinding-sicher). Keine Keep-Alive-Wiederverwendung, `trust_env=False` (keine Umgehung über Env-Proxys).
  - Antwortgröße auf 10 MB begrenzt (Content-Length und gestreamt).
- ICS- und CalDAV-Connector nutzen standardmäßig diesen Client, Redirects sind deaktiviert.
- Generische Fehlermeldungen ohne Statuscode, URL oder Zugangsdaten; unerwartete Ausnahmen werden in `last_sync_error` nur noch generisch gespeichert.
- Einstellung `CALENDAR_ALLOW_INSECURE_URLS` (Default `false`) als Dev-Opt-in für `http://` und lokale Testserver; `production_guard` verweigert den Start, wenn sie in Produktion aktiv ist.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `calendar-connector`: SSRF-Schutz für benutzerdefinierte Kalender-URLs.

## Impact

- Backend: `url_guard.py` (neu), ICS-/CalDAV-Connector, `http_policy.py`, Router `calendar_integrations.py`, `sync_service.run_sync`, `config.py`.
- Betrieb: Kalenderserver müssen per HTTPS unter öffentlicher Adresse erreichbar sein; ausgehende Proxys werden für Kalenderabrufe nicht verwendet.
- Restrisiko: keines bzgl. DNS-Rebinding für die verwendete Verbindung (IP-Pinning). Bestehende Integrationen mit unzulässiger URL schlagen beim nächsten Sync mit generischem Fehler fehl, bis die URL korrigiert ist.
