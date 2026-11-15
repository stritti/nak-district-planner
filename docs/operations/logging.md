# Logging

Dieses Dokument ist die maßgebliche Quelle für das Logging-Konzept des NAK District Planner. Der Umsetzungsstand wird über den OpenSpec-Change `application-logging-concept` in [`openspec/changes`](https://github.com/stritti/nak-district-planner/tree/main/openspec/changes) nachverfolgt; das verbindliche Soll-Verhalten steht in der OpenSpec-Capability `logging`.

## Zweck und Abgrenzung

Application-Logging dient Betrieb und Diagnose: Es macht nachvollziehbar, was die Anwendung zur Laufzeit tut und warum ein Request oder Job fehlschlägt. Es ist **kein** Ersatz für die anderen Protokolle:

| Protokoll | Zweck | Maßgebliche Quelle |
| --- | --- | --- |
| Application-Logs (dieses Dokument) | Betrieb, Diagnose, Korrelation | diese Seite, OpenSpec `logging` |
| Audit-Log (`audit_logs` in der Datenbank) | Security- und Governance-Nachweis von Aktionen und abgelehnten Zugriffen | [Audit Logging](/security/audit-logging), OpenSpec `audit-logging` |
| OpenTelemetry-Traces und -Metriken | Verteiltes Tracing, Leistungsanalyse | [OpenTelemetry](/operations/opentelemetry) |
| Access-/Error-Logs der Proxys (nginx, externer TLS-Proxy) | HTTP-Zugriff auf Infrastruktur-Ebene | [Production Runbook](/operations/production-runbook) §1.1a |

Regel: Was in `audit_logs` gehört (wer hat was geändert oder wurde abgelehnt), wird dort persistiert und nicht zusätzlich als Anwendungslog geschrieben. Umgekehrt landen Diagnosedetails, die nicht audit-relevant sind, nicht in `audit_logs`.

## Log-Pipelines

| Pipeline | Quelle | Senke |
| --- | --- | --- |
| Backend-API | uvicorn (Access/Error) und Anwendungslogger (`app.*`) | stdout des Containers (`docker compose logs backend`) |
| Celery Worker und Beat | Celery-Logger und Anwendungslogger | stdout der Container (`--loglevel` aus Compose) |
| Frontend (Browser) | `console.*` bzw. zentrale Frontend-Logger-Funktion | Browser-Konsole; in Produktion nur Fehler, nie personenbezogene Daten |
| nginx (Frontend- und Backend-Proxy) | Access-/Error-Log | definierte Log-Dateien mit Redaction, siehe Runbook |

Die Anwendung selbst schreibt **keine** Log-Dateien; stdout/stderr ist die einzige Senke. Rotation und Aufbewahrung übernimmt der Container-Runtime (Docker-Logging-Driver bzw. journald).

## Format

- **Produktion:** strukturiertes JSON, ein Objekt pro Zeile (JSON Lines) auf stdout.
- **Entwicklung (`APP_ENV=development`):** lesbares Textformat.
- Umschaltung über `LOG_FORMAT=json|text` (Default: `json`, außer in Entwicklung `text`).

Pflichtfelder jedes JSON-Logeintrags:

| Feld | Inhalt |
| --- | --- |
| `timestamp` | UTC, ISO 8601 |
| `level` | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `logger` | Name des Loggers (Modul), z. B. `app.main` |
| `message` | Logmeldung |
| `service` | `backend` / `worker` / `beat` |
| `env` | Wert von `APP_ENV` |
| `version` | `APP_VERSION` des Deployments |
| `request_id` | Korrelations-ID, falls der Eintrag im Request-Kontext entsteht |
| `task_id` | Celery-Task-ID, falls der Eintrag in einem Task entsteht |
| `exception` | bei Fehlern: Typ, Meldung und redigierter Stacktrace |

## Log-Level

Der Level ist über `LOG_LEVEL` konfigurierbar (Default: `INFO`). `LOG_LEVEL=DEBUG` in Produktion (`APP_ENV=production`) wird mit einer Warnung abgelehnt und auf `INFO` zurückgesetzt.

Richtlinien:

- **ERROR:** Request oder Job ist fehlgeschlagen; immer mit `request_id` bzw. `task_id`.
- **WARNING:** unerwarteter, aber beherrschter Zustand (z. B. Retry, Fallback, Rate-Limiter ohne erreichbares Valkey).
- **INFO:** Lebenszyklus-Ereignisse (Start, Shutdown, erfolgreiche OIDC-Discovery, Schema-Prüfung) — nicht pro Request.
- **DEBUG:** nur in Entwicklung; niemals Request-Payloads.
- Health-Endpunkte (`/health`, `/api/health`) und abgewiesene Rate-Limit-Requests werden nicht auf INFO geloggt.

## Secrets und personenbezogene Daten

- Die process-weite Redaction (`install_log_redaction()`, siehe `app/adapters/api/log_redaction.py`) bleibt auf **allen** Handlern installiert und filtert ICS-Export-Tokens aus Nachricht, Traceback und Stack — auch in Dritt-Loggern wie `uvicorn.access`.
- Es werden **nie** geloggt: Passwörter, Tokens, Credentials, E-Mail-Adressen, Namen, vollständige Request-Payloads und URLs mit Query-Strings. Request-Pfade nur über `redact_secret_path()`.
- Credential-Spalten werden ausschließlich in `audit_logs` unter `changes.redacted_fields` namentlich geführt (OpenSpec `audit-logging`).
- Dieselben Regeln gelten für OTel-Span-Attribute und Metrik-Labels (siehe Change `external-ics-proxy-redaction`).

## Korrelation

- Jeder HTTP-Request erhält genau eine `request_id` (UUID). Ein vom Client gesendeter `X-Request-ID`-Header wird nur von Peers aus `TRUSTED_PROXIES` übernommen (gleiche Vertrauensregel wie die Client-IP, OpenSpec `request-identity`), sonst wird eine neue ID generiert.
- Die `request_id` steht in jedem Log-Eintrag des Requests (über einen `logging.Filter` mit `contextvars`), im Audit-Eintrag (`audit_logs.request_id`) und wird als OTel-Span-Attribut gesetzt.
- Celery-Tasks loggen `task_id` und `task_name`; Beat-Läufe sind über den Service-Namen `beat` identifizierbar.

## Aufbewahrung, Zugriff und Auswertung

- Lokale Aufbewahrung über den Docker-Logging-Driver (begrenzte Größe/Anzahl, siehe Compose); zentrale Aggregation ist optional und außerhalb des Repo-Pflichtumfangs.
- Auswertung und Export erfolgen ausschließlich redigiert über `nakctl logs analyze` bzw. `nakctl logs export` (siehe [Admin-Skripte](/operations/admin-scripts)).
- Zugriff auf Logs ist auf Administratoren beschränkt; Logs gelten als schützenswert, weil sie Metadaten (Zeiten, IPs, User-Agents) enthalten können.

## Betrieb und Alarmierung

- Fehlgeschlagene Requests (5xx), Audit-Persistenzfehler und abgelehnte Requests werden über bestehende Zähler erfasst und zusätzlich als ERROR geloggt — ohne Payload-Daten (OpenSpec `audit-logging`).
- `nakctl check all` und `nakctl logs analyze --fail-on-errors` sind die Standard-Prüfungen für Log-Fehler (siehe Runbook).

## Non-Goals

- Kein Ersatz für das Audit-Log in der Datenbank.
- Keine verpflichtende zentrale Log-Aggregation (OTLP/HTTP an einen Collector ist optional, siehe [OpenTelemetry](/operations/opentelemetry)).
- Kein clientseitiges Error-Tracking: Das Frontend sendet keine Browser-Logs an den Server.
