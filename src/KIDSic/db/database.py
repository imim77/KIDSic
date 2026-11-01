"""An application-lifetime pool; never run migrations during request handling."""

from contextlib import asynccontextmanager
import json
import os

import asyncpg


async def _configure_connection(connection: asyncpg.Connection):
    for name in ("json", "jsonb"):
        await connection.set_type_codec(
            name, schema="pg_catalog", encoder=json.dumps, decoder=json.loads,
            format="text",
        )


@asynccontextmanager
async def database_pool(dsn: str | None = None, *, min_size: int = 1, max_size: int = 10):
    """Borrow with pool.acquire(); use connection.transaction() for atomic writes."""
    url = dsn or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL.")
    async with asyncpg.create_pool(
        dsn=url, min_size=min_size, max_size=max_size,
        command_timeout=30, init=_configure_connection,
    ) as pool:
        yield pool
