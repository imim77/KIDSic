"""Separate write Unit of Work; search keeps its read-only snapshot contract."""
from abc import ABC, abstractmethod

import asyncpg

from KIDSic.dao.interfaces.source import SourceRepository
from KIDSic.exceptions import PersistenceError


class SourceUnitOfWork(ABC):
    sources: SourceRepository

    @abstractmethod
    async def __aenter__(self):
        """Open the import transaction."""

    @abstractmethod
    async def __aexit__(self, exc_type, exc, traceback):
        """Commit on success, otherwise roll back."""


class AsyncpgSourceUnitOfWork(SourceUnitOfWork):
    def __init__(self, pool):
        self._pool = pool
        self._connection = None

    async def __aenter__(self):
        from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository

        if self._connection is not None:
            raise RuntimeError('Source Unit of Work is already open.')
        self._connection = await self._pool.acquire()
        try:
            self._transaction = self._connection.transaction()
            await self._transaction.start()
            # Serialize all source writers, including cross-source object matching.
            await self._connection.execute('SELECT pg_advisory_xact_lock(194733, 1)')
            self.sources = AsyncpgSourceRepository(self._connection)
            return self
        except BaseException:
            try:
                if self._connection.is_in_transaction():
                    await self._transaction.rollback()
            finally:
                await self._pool.release(self._connection)
                self._connection = None
            raise

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            await self._transaction.__aexit__(exc_type, exc, traceback)
        except asyncpg.PostgresError as error:
            raise PersistenceError('Source transaction failed and was rolled back.') from error
        finally:
            await self._pool.release(self._connection)
            self._connection = None
