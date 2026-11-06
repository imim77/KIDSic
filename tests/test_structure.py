"""Infrastructure and service wiring checks independent of external sources."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from KIDSic.config.settings import Settings


class ServiceWiringTests(unittest.IsolatedAsyncioTestCase):

    def test_settings_reject_invalid_pool_and_non_postgres_urls(self):
        for values in ({'database_url':'sqlite://'}, {'database_url':'postgresql://host/db','pool_min_size':5,'pool_max_size':1}):
            with self.assertRaises(ValueError):
                Settings(**values)
