# OpenTelemetry

Der NAK District Planner unterstützt **verteiltes Tracing** über den [OpenTelemetry](https://opentelemetry.io/)-Standard.
Traces werden per OTLP/HTTP an einen konfigurierbaren Collector exportiert und können von jedem kompatiblen Backend
(z. B. Jaeger, Grafana Tempo, Honeycomb) visualisiert werden.

::: info Standard
OpenTelemetry ist per Standard **deaktiviert**. Es entstehen keinerlei Overhead oder Netzwerkverbindungen, solange
`OTEL_ENABLED` nicht explizit auf `true` gesetzt wird.
:::

## Konfiguration

Alle Einstellungen werden über Umgebungsvariablen gesteuert (oder in der `.env`-Datei gesetzt):

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `OTEL_ENABLED` | `false` | Tracing aktivieren (`true` / `false`) |
| `OTEL_SERVICE_NAME` | `nak-district-planner-backend` | Name des Service im Tracing-Backend |
| `OTEL_ENDPOINT` | `http://localhost:4318` | Basis-URL des OTLP/HTTP-Collectors |

Die Spans werden an `{OTEL_ENDPOINT}/v1/traces` exportiert.

## Instrumentierte Komponenten

Wenn Tracing aktiviert ist, werden folgende Komponenten automatisch instrumentiert:

| Komponente | Beschreibung |
| --- | --- |
| **FastAPI** | Alle eingehenden HTTP-Anfragen mit Route, Methode und Status-Code |
| **SQLAlchemy** | Datenbankabfragen als Spans mit SQL-Statement |
| **HTTPX** | Ausgehende HTTP-Aufrufe (z. B. externe Kalender-Provider) |
| **Celery** | Hintergrundtasks (Sync, Feiertags-Import, Cleanup) |

## Aktivierung

### Lokale Entwicklung

In der Datei `services/backend/.env` folgende Zeilen hinzufügen:

```dotenv
OTEL_ENABLED=true
OTEL_SERVICE_NAME=nak-district-planner-backend
OTEL_ENDPOINT=http://localhost:4318
```

### Docker Compose

Für die lokale Entwicklung kann ein Jaeger-Container als All-in-One-Collector hinzugefügt werden:

```yaml
# docker-compose.override.yml (Ergänzung)
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"   # Jaeger UI
      - "4318:4318"     # OTLP/HTTP Receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  backend:
    environment:
      - OTEL_ENABLED=true
      - OTEL_ENDPOINT=http://jaeger:4318
```

Anschließend steht die Jaeger-UI unter `http://localhost:16686` zur Verfügung.

::: tip Grafana Tempo
Alternativ kann [Grafana Tempo](https://grafana.com/oss/tempo/) als Collector genutzt werden. Der OTLP/HTTP-Endpoint
ist identisch – nur `OTEL_ENDPOINT` muss auf den Tempo-Dienst zeigen.
:::

## Architektur

Die Telemetrie-Initialisierung erfolgt zentral in `app/telemetry.py`:

```text
  ├── TracerProvider
  │     └── BatchSpanProcessor → OTLPSpanExporter (OTLP/HTTP)
  ├── FastAPIInstrumentor   (wenn fastapi_app übergeben)
  ├── SQLAlchemyInstrumentor (wenn sqlalchemy_engine übergeben)
  ├── HTTPXClientInstrumentor
  └── CeleryInstrumentor
```

- `app/main.py` ruft `setup_telemetry(fastapi_app=app)` direkt nach der App-Erstellung auf.
- `app/celery_app.py` ruft `setup_telemetry()` auf, damit der Worker-Prozess ebenfalls Spans sendet.

::: warning Produktionsbetrieb
In Produktionsumgebungen sollte der Collector (z. B. OpenTelemetry Collector, Grafana Agent) als Sidecar oder
separater Dienst betrieben werden. Der Backend-Container muss den Collector unter `OTEL_ENDPOINT` erreichen können.
:::
