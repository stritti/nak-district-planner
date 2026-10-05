# Deployment-Migrationen

Datenbankmigrationen sind ein eigener Deployment-Schritt. Backend und Worker besitzen nur Runtime-Datenbankrechte und fuehren selbst kein Alembic-Upgrade aus.

## Docker Compose

Der Service `migrate` verwendet `.env.docker.migrate`, fuehrt einmalig `uv run alembic upgrade head` aus und beendet sich danach. Backend und Worker haben eine `service_completed_successfully`-Abhaengigkeit und starten nur nach erfolgreicher Migration.

Fuer ein reproduzierbares Deployment:

```bash
docker compose build
docker compose run --no-deps --rm migrate
docker compose up -d
```

`docker compose run ... migrate` verwendet den im Compose-Service definierten Migrationsbefehl. Es muss kein zusaetzlicher `alembic upgrade head`-Befehl angehaengt werden.

## Lokale Entwicklung

Ein erstmaliges `docker compose up -d` startet den One-shot-Migrationsservice als Abhaengigkeit mit. Nach dem Hinzufuegen oder Auschecken neuer Migrationen sollte die Migration explizit gegen das neu gebaute Backend-Image ausgefuehrt werden:

```bash
docker compose run --no-deps --rm --build migrate
```

Bei lokaler Backend-Ausfuehrung ausserhalb von Docker bleibt der direkte Alembic-Aufruf gueltig:

```bash
cd services/backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Fail-fast-Schema-Pruefung

Der FastAPI-Lifespan fuehrt keine DDL-Anweisung aus. Vor dem Start der Runtime-Komponenten vergleicht er jedoch die in `alembic_version` gespeicherten Revisionen mit dem Alembic-Head des ausgelieferten Codes.

Bei fehlender Versionstabelle, nicht lesbarer Datenbank oder abweichender Revision bricht der Backend-Start mit einem `SchemaVersionError` ab. Der Fehler ist durch Ausfuehren des Deployment-Migrationsschritts zu beheben, nicht durch automatische Runtime-Migrationen.

## Fehlerfall

Wenn `migrate` fehlschlaegt:

1. Backend und Worker nicht erzwingen oder ohne Migration starten.
2. Log des Migration-Service pruefen: `docker compose logs migrate`.
3. Datenbank-Backup und aktuelle Alembic-Revisionskette pruefen.
4. Ursache beheben und `docker compose run --no-deps --rm --build migrate` erneut ausfuehren.
5. Erst nach erfolgreicher Migration `docker compose up -d` ausfuehren.
