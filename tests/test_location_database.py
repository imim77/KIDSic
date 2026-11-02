"""Rollback-only location integration fixtures are synthetic, never real institutions."""
import os
import unittest
from urllib.parse import urlparse
from uuid import uuid4

from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.db.database import database_pool
from KIDSic.dto.location import LocationQuery


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class LocationDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.context = database_pool(dsn)
        self.pool = await self.context.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction()
        await self.tx.start()
        self.repository = AsyncpgLocationRepository(self.c)
        self.batch = uuid4()
        self.source = await self.c.fetchval('''INSERT INTO data_source
            (dataset_key,title,publisher,url,license,import_allowed,active_batch_id)
            VALUES ($1,'Synthetic','Test','https://example.invalid','Test license',true,$2)
            RETURNING id''', str(uuid4()), self.batch)
        self.municipality = await self.c.fetchval('''INSERT INTO municipality(key,name,aliases)
            VALUES ('zagreb','Zagreb','{zagreba}') ON CONFLICT (key)
            DO UPDATE SET aliases=EXCLUDED.aliases RETURNING id''')

    async def asyncTearDown(self):
        await self.tx.rollback()
        await self.pool.release(self.c)
        await self.context.__aexit__(None, None, None)

    async def fixture(self, name='Synthetic', *, city='Zagreb', provider='municipal',
                      coords=(15.98, 45.81), active=True, seat=False):
        institution = await self.c.fetchval('''INSERT INTO kindergarten
            (name,provider_kind,seat_address,seat_settlement,seat_settlement_key)
            VALUES ($1,$2,'Seat 1','Zagreb','zagreb') RETURNING id''', name, provider)
        location = None
        if not seat:
            location = await self.c.fetchval('''INSERT INTO location
                (kindergarten_id,name,settlement,settlement_key,municipality_id,longitude,latitude)
                VALUES ($1,$2,$3,lower($3),$4,$5,$6) RETURNING id''', institution,
                name + ' branch', city, self.municipality if city == 'Sesvete' else None, *coords)
        await self.record(institution, location, active=active)
        return institution, location

    async def record(self, institution, location, *, active=True, source=None):
        await self.c.execute('''INSERT INTO source_record
            (source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method,
             observed_on,fetched_at)
            VALUES ($1,$2,'{}',$3,$4,'accepted','new','2026-10-01','2026-11-02T10:00Z')''',
            source or self.source, self.batch if active else uuid4(), institution, location)

    async def test_active_snapshots_and_deduplication_keep_source_dates(self):
        institution, location = await self.fixture()
        await self.record(institution, location)
        second = await self.c.fetchval('''INSERT INTO data_source
            (dataset_key,title,publisher,url,import_allowed,active_batch_id)
            VALUES ($1,'Second','Test','https://example.invalid/second',true,$2)
            RETURNING id''', str(uuid4()), self.batch)
        await self.record(institution, location, source=second)
        await self.fixture('Inactive', active=False)
        for status in ('candidate', 'rejected'):
            ignored, _ = await self.fixture(status)
            await self.c.execute('UPDATE source_record SET match_status=$2 WHERE kindergarten_id=$1',
                                 ignored, status)
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['location_id'], location)
        self.assertEqual(len(rows[0]['sources']), 2)
        self.assertEqual(rows[0]['sources'][1]['reference_date'], '2026-10-01')
        self.assertTrue(all(source['retrieved_at'] for source in rows[0]['sources']))
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1', second)
        self.assertEqual(len((await self.repository.list_locations(LocationQuery()))[0]['sources']), 1)
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1', self.source)
        self.assertEqual(await self.repository.list_locations(LocationQuery()), [])

    async def test_seat_fallback_and_unlocated_facility_stay_distinct(self):
        seat, _ = await self.fixture('Seat only', seat=True)
        unlocated, _ = await self.fixture('Unlocated', coords=(None, None))
        outside, _ = await self.fixture('Outside', city='Other town')
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual({r['kindergarten_id'] for r in rows}, {seat, unlocated})
        self.assertEqual({r['location_role'] for r in rows}, {'seat', 'facility'})
        self.assertTrue(all(r['longitude'] is None for r in rows))
        self.assertNotIn(outside, [r['kindergarten_id'] for r in rows])
        self.assertEqual(await self.repository.list_locations(
            LocationQuery(bbox=(15, 45, 16, 46))), [])

    async def test_municipality_name_literal_query_provider_and_inclusive_bbox(self):
        _, location = await self.fixture('100% Medo', city='Sesvete', provider='private')
        await self.fixture('Other municipal')
        query = LocationQuery(city='zagreba', q='100%', provider_kind='private',
                              bbox=(15.98, 45.81, 16, 46))
        self.assertEqual([r['location_id'] for r in await self.repository.list_locations(query)],
                         [location])
        self.assertEqual(await self.repository.list_locations(LocationQuery(q='missing')), [])
        self.assertEqual(await self.repository.list_locations(LocationQuery(city='Split')), [])

    async def test_complete_city_has_no_recommendation_limit(self):
        for i in range(101):
            await self.fixture(f'Facility {i}')
        self.assertEqual(len(await self.repository.list_locations(LocationQuery())), 101)
