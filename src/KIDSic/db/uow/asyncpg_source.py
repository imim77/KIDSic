"""AsyncpgSourceUnitOfWork serializes atomic source imports."""
import asyncpg
from KIDSic.db.uow.source import SourceUnitOfWork
from KIDSic.exceptions import PersistenceError
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dao.concrete.asyncpg_historical import AsyncpgHistoricalRepository
from KIDSic.dao.concrete.asyncpg_enrolment import AsyncpgEnrolmentDocumentRepository


class AsyncpgSourceUnitOfWork(SourceUnitOfWork):
    def __init__(self, pool):
        self._pool = pool
        self._connection = None

    async def __aenter__(self):
        if self._connection is not None:
            raise RuntimeError('Source Unit of Work is already open.')
        try:
            self._connection = await self._pool.acquire()
        except (asyncpg.PostgresError, asyncpg.InterfaceError) as error:
            raise PersistenceError('Database connection could not be acquired.') from error
        try:
            self._transaction = self._connection.transaction()
            await self._transaction.start()

            await self._connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            self.sources = AsyncpgSourceRepository(self._connection)
            self.historical = AsyncpgHistoricalRepository(self._connection)
            self.enrolment = AsyncpgEnrolmentDocumentRepository(self._connection)
            return self
        except BaseException as error:
            try:
                if self._connection.is_in_transaction():
                    await self._transaction.rollback()
            finally:
                await self._pool.release(self._connection)
                self._connection = None
            if isinstance(error, (asyncpg.PostgresError, asyncpg.InterfaceError)):
                raise PersistenceError('Import transaction could not be opened.') from error
            raise

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            await self._transaction.__aexit__(exc_type, exc, traceback)
            if isinstance(exc, (asyncpg.PostgresError, asyncpg.InterfaceError)):
                raise PersistenceError('Source transaction failed and was rolled back.') from exc
        except (asyncpg.PostgresError, asyncpg.InterfaceError) as error:
            raise PersistenceError('Source transaction failed and was rolled back.') from error
        finally:
            await self._pool.release(self._connection)
            self._connection = None
