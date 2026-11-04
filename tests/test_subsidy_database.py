"""Subsidy seed verifies persistence and keeps unconfirmed amounts unknown."""
import os
from pathlib import Path
import unittest
from urllib.parse import urlparse

import asyncpg

from KIDSic.db.database import database_pool


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class SubsidyDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.context = database_pool(dsn)
        self.pool = await self.context.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction()
        await self.tx.start()
        for key in ('zagreb', 'varazdin', 'rijeka'):
            await self.c.execute('INSERT INTO municipality(key,name) VALUES ($1,$1) '
                                 'ON CONFLICT (key) DO NOTHING', key)
        sql = (Path(__file__).resolve().parents[1] / 'src/KIDSic/db/seeds/'
               '2026-11-04_municipal_subsidies.sql').read_text()
        # Keep the production seed inside the fixture's rollback transaction.
        self.seed = sql.replace('\nBEGIN;\n', '\n').replace('\nCOMMIT;\n', '\n')

    async def asyncTearDown(self):
        await self.tx.rollback()
        await self.pool.release(self.c)
        await self.context.__aexit__(None, None, None)

    async def test_seed_replays_without_changing_facilities_or_policy_identities(self):
        before = await self.c.fetch('SELECT id FROM kindergarten ORDER BY id')
        await self.c.execute(self.seed)
        policies = await self.c.fetch('SELECT * FROM municipality_subsidy_policy ORDER BY policy_key')
        self.assertEqual(len(policies), 9)
        await self.c.execute(self.seed)
        self.assertEqual(policies, await self.c.fetch(
            'SELECT * FROM municipality_subsidy_policy ORDER BY policy_key'))
        self.assertEqual(before, await self.c.fetch('SELECT id FROM kindergarten ORDER BY id'))
        self.assertEqual(await self.c.fetchval(
            "SELECT count(*) FROM municipality_subsidy_policy WHERE 'unknown'=ANY(provider_kinds) "
            "OR 'other'=ANY(provider_kinds)"), 0)
        rows = {row['policy_key']: row for row in policies}
        childminder = rows['varazdin-childminder-20261104']
        self.assertEqual(childminder['verification_status'], 'partial')
        self.assertIsNone(childminder['rules']['city_subsidy_cents'])
        rijeka = rows['rijeka-childminder-20261104']['rules']
        self.assertEqual(rijeka['rates'][0]['city_subsidy_cents'], 26000)
        self.assertEqual(rijeka['pending_change']['status'], 'consultation_not_adopted')
        zagreb = rows['zagreb-private-20261104']['rules']
        for rate in zagreb['rates']:
            self.assertEqual(rate['city_subsidy_cents'],
                             rate['base_city_subsidy_cents'] + rate['fixed_city_top_up_cents'])
        self.assertIsNone(rows['zagreb-municipal-20261104']['rules']['city_subsidy_cents'])

    async def test_missing_city_rolls_back_seed_and_invalid_types_are_rejected(self):
        with self.assertRaises(asyncpg.NotNullViolationError):
            async with self.c.transaction():
                await self.c.execute(self.seed.replace('"municipality_key": "rijeka"',
                                                      '"municipality_key": "missing"'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM municipality_subsidy_policy'), 0)
        await self.c.execute(self.seed)
        with self.assertRaises(asyncpg.CheckViolationError):
            async with self.c.transaction():
                await self.c.execute("UPDATE municipality_subsidy_policy SET provider_kinds=ARRAY['unknown']")
