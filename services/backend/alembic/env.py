import asyncio
from logging.config import fileConfig

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.adapters.db.orm_models
from alembic import context
from app.adapters.db.base import Base
from app.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables managed by migrations alone, without an ORM model. app_superadmin_config
# holds the bootstrap superadmin and is only touched through SQL functions (0017);
# the kombu_*/celery_* tables belong to the Celery broker and result backend;
# service_assignment_duplicates_468 is the owner-only archive of the duplicates
# removed by 20261007_assignment_unique (exists only where duplicates existed).
_SQL_ONLY_TABLES = frozenset(
    {
        "app_superadmin_config",
        "kombu_queue",
        "kombu_message",
        "celery_taskmeta",
        "celery_tasksetmeta",
        "service_assignment_duplicates_468",
    }
)


# Fixed pg_advisory_lock key ("nakmigr" in ASCII): concurrent `migrate` runs
# serialize instead of applying the same revisions twice.
MIGRATION_LOCK_KEY = 0x6E616B6D696772


def _include_object(obj, name, type_, reflected, compare_to) -> bool:
    return not (type_ == "table" and name in _SQL_ONLY_TABLES)


def _migration_database_url() -> str:
    return settings.migration_database_url or settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_migration_database_url(),
        target_metadata=target_metadata,
        include_object=_include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    # Session-level lock: survives the migration transaction's commit and is
    # released explicitly (or by PostgreSQL when the connection closes).
    connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY})
    connection.commit()
    try:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=_include_object
        )
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.rollback()
        connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})
        connection.commit()


async def run_migrations_online() -> None:
    connectable = create_async_engine(_migration_database_url(), echo=False)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
