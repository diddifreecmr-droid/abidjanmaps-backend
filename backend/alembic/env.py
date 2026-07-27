from __future__ import annotations

import asyncio
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic runs through its own CLI entry point, so make the backend package
# resolvable whether the command is started locally or inside Docker.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.modules.local_enrichment.infrastructure.persistence import models as enrichment_models
from app.modules.journeys.infrastructure.persistence import models as journey_models
from app.modules.map_data.infrastructure.persistence import models as map_data_models
from app.modules.users.infrastructure.persistence import models as user_models
from app.shared.configuration.settings import settings
from app.shared.infrastructure.persistence.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.database_url)
MANAGED_TABLES = set(target_metadata.tables)


def include_object(object_, name: str, type_: str, reflected: bool, compare_to) -> bool:
    """Ignore PostGIS/Tiger extension objects not owned by AbidjanMaps."""
    if type_ == "table":
        return name in MANAGED_TABLES

    table = getattr(object_, "table", None)
    if table is not None and reflected and compare_to is None:
        return table.name in MANAGED_TABLES

    return True


def run_migrations_offline() -> None:
    # Alembic only renders SQL in this mode, so it needs the PostgreSQL dialect
    # name rather than the async runtime driver name.
    url = config.get_main_option("sqlalchemy.url").replace("+asyncpg", "")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
