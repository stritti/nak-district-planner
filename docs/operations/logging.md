# Logging

Dieses Dokument ist die maßgebliche Quelle für das Logging-Konzept des NAK District Planner. Das verbindliche Verhalten steht in der OpenSpec-Capability `logging` (eingeführt mit dem Change `application-logging-concept`); die Umsetzung liegt in `app/logging_config.py`, `app/adapters/api/middleware/request_id.py` und `services/frontend/src/utils/logger.ts`.

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
| Backend-API | eigenes Access-Log (`app.access`), uvicorn-Error-Log und Anwendungslogger (`app.*`) | stdout des Containers (`docker compose logs backend`) |
| Celery Worker und Beat | Celery-Logger und Anwendungslogger, gleiches Format wie das Backend | stdout der Container; Level aus `LOG_LEVEL` (das `--loglevel` in Compose wird dabei nicht verwendet) |
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
| `task_name` | Name des Celery-Tasks, falls der Eintrag in einem Task entsteht |
| `exception` | bei Fehlern: Typ, Meldung und redigierter Stacktrace |

Access-Log-Einträge (Logger `app.access`) enthalten zusätzlich `method`, `path` (redigiert, ohne Query-String), `status` und `duration_ms`. Das uvicorn-eigene Access-Log ist abgeschaltet, weil es keine Dauer kennt.

## Log-Level

Der Level ist über `LOG_LEVEL` konfigurierbar (Default: `INFO`). `LOG_LEVEL=DEBUG` in Produktion (`APP_ENV=production`) wird mit einer Warnung abgelehnt und auf `INFO` zurückgesetzt; der Start wird dabei bewusst nicht abgebrochen. Ungültige Werte für `LOG_LEVEL` oder `LOG_FORMAT` verhindern dagegen den Start.

Richtlinien:

- **ERROR:** Request oder Job ist fehlgeschlagen; immer mit `request_id` bzw. `task_id`.
- **WARNING:** unerwarteter, aber beherrschter Zustand (z. B. Retry, Fallback, Rate-Limiter ohne erreichbares Valkey).
- **INFO:** Lebenszyklus-Ereignisse (Start, Shutdown, erfolgreiche OIDC-Discovery, Schema-Prüfung) — nicht pro Request.
- **DEBUG:** nur in Entwicklung; niemals Request-Payloads.
- Health-Endpunkte (`/health`, `/api/health`) und vom Rate-Limiter abgewiesene Requests (429) erzeugen keine Access-Log-Zeile auf INFO, nur auf DEBUG. Ein fehlschlagender Health-Check (5xx, z. B. Datenbank oder Valkey nicht erreichbar) wird dagegen als ERROR geloggt.

## Secrets und personenbezogene Daten

- Die process-weite Redaction (`install_log_redaction()`, siehe `app/adapters/api/log_redaction.py`) bleibt auf **allen** Handlern installiert und filtert ICS-Export-Tokens aus Nachricht, Traceback und Stack — auch in Dritt-Loggern wie `uvicorn.access`.
- Die Redaction gilt für beide Formate (JSON und Text) und auch für die Celery-Logger.
- Es werden **nie** geloggt: Passwörter, Tokens, Credentials, E-Mail-Adressen, Namen, vollständige Request-Payloads und URLs mit Query-Strings. Request-Pfade nur über `redact_secret_path()`.
- Der Frontend-Logger maskiert Werte von Schlüsseln, die `token`, `password`, `secret`, `credential`, `email` oder `name` enthalten (auch verschachtelt), als `[redacted]`.
- Credential-Spalten werden ausschließlich in `audit_logs` unter `changes.redacted_fields` namentlich geführt (OpenSpec `audit-logging`).
- Dieselben Regeln gelten für OTel-Span-Attribute und Metrik-Labels (siehe Change `external-ics-proxy-redaction`).

## Korrelation

- Jeder HTTP-Request erhält genau eine `request_id`. Der Frontend-nginx erzeugt sie für jeden Request selbst (`$request_id`) und überschreibt einen vom Browser oder vom externen TLS-Proxy mitgeschickten `X-Request-ID`-Header; Clients können die ID also nicht wählen.
- Das Backend übernimmt `X-Request-ID` nur von Peers aus `TRUSTED_PROXIES` (gleiche Vertrauensregel wie die Client-IP, OpenSpec `request-identity`) und nur im Format `[A-Za-z0-9-]`, höchstens 64 Zeichen. Sonst, etwa bei direktem Zugriff auf Port 8000, wird eine neue UUID erzeugt.
- Die `request_id` steht in jedem Log-Eintrag des Requests (über einen `logging.Filter` mit `contextvars`), im Audit-Eintrag (`audit_logs.request_id`) und wird als OTel-Span-Attribut gesetzt.
- Celery-Tasks loggen `task_id` und `task_name`; Worker- und Beat-Zeilen sind über `service=worker` bzw. `service=beat` unterscheidbar.

## Aufbewahrung, Zugriff und Auswertung

- Lokale Aufbewahrung über den Docker-Logging-Driver (begrenzte Größe/Anzahl, siehe Compose); zentrale Aggregation ist optional und außerhalb des Repo-Pflichtumfangs.
- Auswertung und Export erfolgen ausschließlich redigiert über `nakctl logs analyze` bzw. `nakctl logs export` (siehe [Admin-Skripte](/operations/admin-scripts)).
- Zugriff auf Logs ist auf Administratoren beschränkt; Logs gelten als schützenswert, weil sie Metadaten (Zeiten, IPs, User-Agents) enthalten können.

## Betrieb und Alarmierung

- Fehlgeschlagene Requests (5xx) erscheinen als Access-Log-Zeile auf ERROR, Audit-Persistenzfehler werden als ERROR geloggt, Audit-Persistenzfehler zusätzlich gezählt — ohne Payload-Daten (OpenSpec `audit-logging`).
- Abgelehnte Requests (403) sind kein Fehler der Anwendung: Sie werden in `audit_logs` (`ACCESS_DENIED`) nachgewiesen und erscheinen im Anwendungslog nur als normale Access-Log-Zeile, nicht als ERROR.
- `nakctl check all` und `nakctl logs analyze --fail-on-errors` sind die Standard-Prüfungen für Log-Fehler (siehe Runbook).

## Non-Goals

- Kein Ersatz für das Audit-Log in der Datenbank.
- Keine verpflichtende zentrale Log-Aggregation (OTLP/HTTP an einen Collector ist optional, siehe [OpenTelemetry](/operations/opentelemetry)).
- Kein clientseitiges Error-Tracking: Das Frontend sendet keine Browser-Logs an den Server.
