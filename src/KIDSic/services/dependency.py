"""Own infrastructure lifetime and assemble services for commands/API handlers."""
from contextlib import asynccontextmanager
import httpx
import asyncpg
from KIDSic.exceptions import PersistenceError

from KIDSic.config.settings import Settings
from KIDSic.db.database import database_pool
from KIDSic.db.uow.asyncpg import AsyncpgUnitOfWork
from KIDSic.factories.location import LocationServiceFactory
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.factories.historical import HistoricalServiceFactory
from KIDSic.factories.enrolment import EnrolmentDocumentServiceFactory
from KIDSic.factories.rag import RagServiceFactory
from KIDSic.db.uow.asyncpg_source import AsyncpgSourceUnitOfWork


class DependencyService:
    def __init__(self, settings: Settings):
        self._settings = settings

    @asynccontextmanager
    async def source_service(self, *, with_database: bool = True, source_keys=None):
        async with httpx.AsyncClient(headers={'User-Agent': 'KIDSic/0.1',
                                             'Accept': 'application/json'}) as http:
            factory = SourceServiceFactory(self._settings)
            if not with_database:
                yield factory.create(http, source_keys=source_keys)
            else:
                async with self._pool() as pool:
                    yield factory.create(http, lambda: AsyncpgSourceUnitOfWork(pool), source_keys)

    @asynccontextmanager
    async def historical_service(self, *, with_database: bool = True, source_keys=None):
        async with httpx.AsyncClient(headers={'User-Agent': 'KIDSic/0.1'}) as http:
            factory = HistoricalServiceFactory(self._settings)
            if not with_database:
                yield factory.create(http, source_keys=source_keys)
            else:
                async with self._pool() as pool:
                    yield factory.create(http, lambda: AsyncpgSourceUnitOfWork(pool), source_keys)

    @asynccontextmanager
    async def enrolment_service(self, *, with_database: bool = True):
        if not with_database:
            yield EnrolmentDocumentServiceFactory().create()
        else:
            async with self._pool() as pool:
                yield EnrolmentDocumentServiceFactory().create(lambda: AsyncpgSourceUnitOfWork(pool))

    @asynccontextmanager
    async def conversation_services(self):
        async with self._pool() as pool:
            def work():
                return AsyncpgUnitOfWork(pool)
            yield LocationServiceFactory().create(work), RagServiceFactory().create(work)

    @asynccontextmanager
    async def location_service(self):
        async with self._pool() as pool:
            yield LocationServiceFactory().create(lambda: AsyncpgUnitOfWork(pool))

    @asynccontextmanager
    async def _pool(self):
        try:
            async with database_pool(self._settings.database_url,
                                     min_size=self._settings.pool_min_size,
                                     max_size=self._settings.pool_max_size) as pool:
                yield pool
        except (asyncpg.PostgresError, asyncpg.InterfaceError) as error:
            raise PersistenceError('Database operation failed.') from error
