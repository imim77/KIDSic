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


USER_AGENT = 'KIDSic/0.1'


class DependencyService:
    """DependencyService opens each resource a service needs and closes it
    when the caller's block ends. Dry runs pass with_database=False to read
    sources without a database."""
    def __init__(self, settings: Settings):
        self._settings = settings

    @asynccontextmanager
    async def source_service(self, *, with_database: bool = True, source_keys=None):
        async with httpx.AsyncClient(headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}) as http, \
                self._source_work(with_database) as work:
            yield SourceServiceFactory(self._settings).create(http, work, source_keys)

    @asynccontextmanager
    async def historical_service(self, *, with_database: bool = True, source_keys=None):
        async with httpx.AsyncClient(headers={'User-Agent': USER_AGENT}) as http, \
                self._source_work(with_database) as work:
            yield HistoricalServiceFactory(self._settings).create(http, work, source_keys)

    @asynccontextmanager
    async def enrolment_service(self, *, with_database: bool = True):
        async with self._source_work(with_database) as work:
            yield EnrolmentDocumentServiceFactory().create(work)

    @asynccontextmanager
    async def conversation_services(self):
        async with self._read_work() as work:
            yield LocationServiceFactory().create(work), RagServiceFactory().create(work)

    @asynccontextmanager
    async def location_service(self):
        async with self._read_work() as work:
            yield LocationServiceFactory().create(work)

    @asynccontextmanager
    async def _source_work(self, with_database: bool):
        """_source_work yields an import Unit of Work factory, or None for a dry run."""
        if not with_database:
            yield None
            return
        async with self._pool() as pool:
            yield lambda: AsyncpgSourceUnitOfWork(pool)

    @asynccontextmanager
    async def _read_work(self):
        async with self._pool() as pool:
            yield lambda: AsyncpgUnitOfWork(pool)

    @asynccontextmanager
    async def _pool(self):
        try:
            async with database_pool(self._settings.database_url,
                                     min_size=self._settings.pool_min_size,
                                     max_size=self._settings.pool_max_size) as pool:
                yield pool
        except (asyncpg.PostgresError, asyncpg.InterfaceError) as error:
            raise PersistenceError('Database operation failed.') from error
