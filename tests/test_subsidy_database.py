"""Subsidy seed verifies persistence and keeps unconfirmed amounts unknown."""
import os
from pathlib import Path
import unittest
from urllib.parse import urlparse

import asyncpg
from uuid import uuid4

from KIDSic.db.database import database_pool
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dto.location import LocationQuery


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

    async def test_location_uses_facility_city_and_type_and_excludes_inactive_periods(self):
        await self.c.execute(self.seed)
        cities = {r['key']: r['id'] for r in await self.c.fetch('SELECT key,id FROM municipality')}
        batch = uuid4()
        source = await self.c.fetchval("""INSERT INTO data_source
            (dataset_key,title,publisher,url,import_allowed,active_batch_id)
            VALUES ('subsidy-test','Test','Test','https://example.invalid',true,$1) RETURNING id""", batch)
        for kind in ('private', 'unknown'):
            owner = await self.c.fetchval("""INSERT INTO kindergarten
                (name,provider_kind) VALUES ('Test',$1) RETURNING id""",
                kind)
            await self.c.execute('INSERT INTO kindergarten_seat(kindergarten_id,municipality_id) VALUES ($1,$2)', owner,cities['zagreb'])
            location = await self.c.fetchval("""INSERT INTO location
                (kindergarten_id,name,settlement,settlement_key,municipality_id)
                VALUES ($1,'Rijeka branch','Rijeka','rijeka',$2) RETURNING id""", owner, cities['rijeka'])
            await self.c.execute("""INSERT INTO source_record
                (source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method)
                VALUES ($1,$2,'{}',$3,$4,'accepted','manual')""", source, batch, owner, location)
        repo = AsyncpgLocationRepository(self.c)
        rows = await repo.list_locations(LocationQuery(city='Rijeka'))
        private = next(r for r in rows if r['provider_kind'] == 'private')
        self.assertEqual([p['policy_key'] for p in private['subsidy_policies']], ['rijeka-private-20261104'])
        self.assertEqual(next(r for r in rows if r['provider_kind'] == 'unknown')['subsidy_policies'], [])
        await self.c.execute("""UPDATE municipality_subsidy_policy
            SET valid_until=CURRENT_DATE-1 WHERE policy_key='rijeka-private-20261104'""")
        self.assertTrue(all(not r['subsidy_policies'] for r in await repo.list_locations(LocationQuery(city='Rijeka'))))
        await self.c.execute("""UPDATE municipality_subsidy_policy
            SET valid_from=CURRENT_DATE+1,valid_until=NULL WHERE policy_key='rijeka-private-20261104'""")
        self.assertTrue(all(not r['subsidy_policies'] for r in await repo.list_locations(LocationQuery(city='Rijeka'))))
