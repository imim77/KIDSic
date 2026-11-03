"""Asyncpg implementation of the read-only Unit of Work."""
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
        self._connection = await self._pool.acquire()
        try:
            self._transaction = self._connection.transaction(isolation='repeatable_read', readonly=True)
            await self._transaction.start()
            self.search = AsyncpgKindergartenRepository(self._connection)
            self.locations = AsyncpgLocationRepository(self._connection)
            return self
        except BaseException:
            await self._pool.release(self._connection)
            self._connection = None
            raise

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            await self._transaction.__aexit__(exc_type, exc, traceback)
        finally:
            await self._pool.release(self._connection)
            self._connection = None
