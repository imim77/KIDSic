"""Settings validation rejects unsupported databases and inconsistent pools."""

import unittest

from KIDSic.config.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_settings_reject_invalid_pool_and_non_postgres_urls(self):
        for values in (
            {"database_url": "sqlite://"},
            {
                "database_url": "postgresql://host/db",
                "pool_min_size": 5,
                "pool_max_size": 1,
            },
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Settings(**values)
