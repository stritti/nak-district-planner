# Deployment-Migrationen

Datenbankmigrationen sind ein eigener Deployment-Schritt. Backend und Worker besitzen nur Runtime-Datenbankrechte und fuehren selbst kein Alembic-Upgrade aus.

## Docker Compose

Der Service `migrate` verwendet `.env.db` und `.env.docker.migrate`, fuehrt einmalig `uv run alembic upgrade head` aus und beendet sich danach. Backend und Worker haben eine `service_completed_successfully`-Abhaengigkeit und starten nur nach erfolgreicher Migration.

### Credentials

Das PostgreSQL-Owner-Passwort (`POSTGRES_PASSWORD`) steht ausschliesslich in `.env.db` (gitignored, Vorlage `.env.db.example`). Diese Datei laden nur `db`, `db-test` und `migrate`. Backend, Worker und alle weiteren Runtime-Services laden `.env` und `.env.docker` und erhalten damit nur die eingeschraenkte Rolle `APP_DB_USER`. `.env` darf daher kein `POSTGRES_PASSWORD` enthalten; fehlt `.env.db`, bricht `docker compose` bereits beim Laden der Konfiguration ab.

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

Der Celery-Worker fuehrt dieselbe Pruefung beim Start aus (Signal `worker_init`).

Bei fehlender Versionstabelle, nicht lesbarer Datenbank oder abweichender Revision bricht der Start von Backend bzw. Worker mit einem `SchemaVersionError` ab. Der Fehler ist durch Ausfuehren des Deployment-Migrationsschritts zu beheben, nicht durch automatische Runtime-Migrationen.

## Parallele Migrationslaeufe

`alembic/env.py` haelt waehrend des Upgrades einen PostgreSQL-Advisory-Lock mit festem Schluessel. Startet `migrate` mehrfach gleichzeitig (z. B. paralleles `up` und `run`), wartet der zweite Lauf, bis der erste fertig ist, und findet danach den aktuellen Head vor.

## Rollback auf ein aelteres Image

Ein aelteres Image gegen ein bereits neueres Schema startet nicht: Backend und Worker erwarten den Head ihres eigenen Codes und brechen mit `SchemaVersionError` ab (fail closed). Ein Rollback erfordert deshalb entweder ein Restore des vor dem Deployment erstellten Backups oder ein explizites `alembic downgrade` auf die Revision des Ziel-Images, ausgefuehrt mit dem neueren Image (nur dieses kennt die zurueckzunehmenden Revisionen).

## Fehlerfall

Wenn `migrate` fehlschlaegt:

1. Backend und Worker nicht erzwingen oder ohne Migration starten.
2. Log des Migration-Service pruefen: `docker compose logs migrate`.
3. Datenbank-Backup und aktuelle Alembic-Revisionskette pruefen.
4. Ursache beheben und `docker compose run --no-deps --rm --build migrate` erneut ausfuehren.
5. Erst nach erfolgreicher Migration `docker compose up -d` ausfuehren.
