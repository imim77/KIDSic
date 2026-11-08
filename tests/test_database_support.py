"""Database fixture checks protect cleanup when setup or a test fails."""

import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from support.database import DatabaseTestCase


class DatabaseCleanupTests(unittest.TestCase):
    def test_resources_close_in_reverse_order_even_after_failure(self):
        for failure in (None, "setup", "test"):
            with self.subTest(failure=failure):
                self.assert_cleanup(failure)

    def assert_cleanup(self, failure):
        events = []

        @asynccontextmanager
        async def resource(name, value):
            events.append(f"open {name}")
            try:
                yield value
            finally:
                events.append(f"close {name}")

        async def rollback():
            events.append("rollback")

        # Match asyncpg's decorated method: a sync call returns a coroutine.
        transaction = SimpleNamespace(
            start=AsyncMock(), rollback=Mock(side_effect=rollback)
        )
        connection = SimpleNamespace(transaction=lambda: transaction)
        pool = SimpleNamespace(acquire=lambda: resource("connection", connection))

        class ExampleTest(DatabaseTestCase):
            async def asyncSetUp(self):
                await super().asyncSetUp()
                if failure == "setup":
                    raise RuntimeError("setup failed")

            async def runTest(self):
                if failure == "test":
                    raise RuntimeError("test failed")

        result = unittest.TestResult()
        with (
            patch.dict(
                "os.environ",
                KIDSIC_TEST_DATABASE_URL="postgresql://localhost/kidsic_test_fixture",
            ),
            patch(
                "support.database.database_pool",
                return_value=resource("pool", pool),
            ),
        ):
            ExampleTest().run(result)

        self.assertEqual(len(result.errors), int(failure is not None))
        self.assertEqual(result.failures, [])
        self.assertEqual(
            events,
            [
                "open pool",
                "open connection",
                "rollback",
                "close connection",
                "close pool",
            ],
        )

    def test_application_database_is_rejected_before_opening_a_pool(self):
        class ExampleTest(DatabaseTestCase):
            async def runTest(self):
                self.fail("The application database must never be opened")

        result = unittest.TestResult()
        with (
            patch.dict(
                "os.environ", KIDSIC_TEST_DATABASE_URL="postgresql://localhost/kidsic"
            ),
            patch("support.database.database_pool") as pool,
        ):
            ExampleTest().run(result)

        pool.assert_not_called()
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Use a disposable kidsic_test_* database", result.errors[0][1])
