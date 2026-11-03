"""Asyncpg implementation of the read-only Unit of Work."""
import asyncpg
from KIDSic.exceptions import PersistenceError
from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.db.uow.base import UnitOfWork


class AsyncpgUnitOfWork(UnitOfWork):
    def __init__(self, pool):
        self._pool = pool
        self._connection = None

    async def __aenter__(self):
        if self._connection is not None:
            raise RuntimeError('Unit of Work is already open.')
        try:
            self._connection = await self._pool.acquire()
        except (asyncpg.PostgresError, asyncpg.InterfaceError) as error:
            raise PersistenceError('Database connection could not be acquired.') from error
        try:
            self._transaction = self._connection.transaction(isolation='repeatable_read', readonly=True)
            await self._transaction.start()
            self.search = AsyncpgKindergartenRepository(self._connection)
            self.locations = AsyncpgLocationRepository(self._connection)
            return self
        except BaseException as error:
            try:
                if self._connection.is_in_transaction():
                    await self._transaction.rollback()
            finally:
                await self._pool.release(self._connection)
                self._connection = None
            if isinstance(error, (asyncpg.PostgresError, asyncpg.InterfaceError)):
                raise PersistenceError('Database snapshot could not be opened.') from error
            raise

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            await self._transaction.__aexit__(exc_type, exc, traceback)
            if isinstance(exc, (asyncpg.PostgresError, asyncpg.InterfaceError)):
                raise PersistenceError('Database read failed.') from exc
        except (asyncpg.PostgresError, asyncpg.InterfaceError) as error:
            raise PersistenceError('Database read failed.') from error
        finally:
            await self._pool.release(self._connection)
            self._connection = None
