"""Own infrastructure lifetime and assemble services for commands/API handlers."""
from contextlib import asynccontextmanager

from KIDSic.config.settings import Settings
from KIDSic.db.database import database_pool
from KIDSic.db.uow.asyncpg import AsyncpgUnitOfWork
from KIDSic.factories.kindergarten_search import KindergartenSearchServiceFactory


class DependencyService:
    def __init__(self, settings: Settings):
        self._settings = settings

    @asynccontextmanager
    async def kindergarten_search_service(self):
        async with database_pool(
            self._settings.database_url,
            min_size=self._settings.pool_min_size,
            max_size=self._settings.pool_max_size,
        ) as pool:
            yield KindergartenSearchServiceFactory().create(lambda: AsyncpgUnitOfWork(pool))
