"""Alembic migrations use SQLAlchemy's async engine with the asyncpg driver."""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)


def database_url():
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL.")
    url = make_url(value)
    if url.get_backend_name() not in {"postgres", "postgresql"}:
        raise ValueError("KIDSic migrations require PostgreSQL.")
    return url.set(drivername="postgresql+asyncpg")


def migrate_connection(connection):
    # The versioned SQL files are authoritative; migrations are authored explicitly.
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


async def migrate_async():
    engine = create_async_engine(database_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate_connection)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=database_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    migrate_connection(config.attributes["connection"])
else:
    asyncio.run(migrate_async())
