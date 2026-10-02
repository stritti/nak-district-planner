import asyncio
from logging.config import fileConfig

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
# holds the bootstrap superadmin and is only touched through SQL functions (0017).
_SQL_ONLY_TABLES = frozenset({"app_superadmin_config"})


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
    context.configure(
        connection=connection, target_metadata=target_metadata, include_object=_include_object
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(_migration_database_url(), echo=False)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
