"""DatabaseTestCase isolates each fixture in a rollback-only transaction."""

import os
import unittest
from urllib.parse import urlparse

from KIDSic.db.database import database_pool


class DatabaseTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ.get("KIDSIC_TEST_DATABASE_URL")
        if not dsn:
            self.skipTest("Set KIDSIC_TEST_DATABASE_URL")
        if not urlparse(dsn).path.removeprefix("/").startswith("kidsic_test_"):
            raise ValueError("Use a disposable kidsic_test_* database.")

        # Register cleanup as resources open, including when subclass setup fails.
        self.pool = await self.enterAsyncContext(database_pool(dsn))
        self.connection = await self.enterAsyncContext(self.pool.acquire())
        transaction = self.connection.transaction()
        await transaction.start()
        self.addAsyncCleanup(self._rollback, transaction)

    async def _rollback(self, transaction):
        # asyncpg decorates rollback with a synchronous coroutine factory.
        await transaction.rollback()
