"""Reviewed geography preserves imported facility identities and address evidence."""
from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from uuid import UUID
from unittest.mock import AsyncMock
from urllib.parse import urlparse

from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.db.database import database_pool
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.source import SourceSnapshot
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from test_rijeka import rijeka_records, rijeka_source

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))  # Scripts import their shared reviewed_snapshot helper.
spec = importlib.util.spec_from_file_location('rijeka_geography', SCRIPTS / 'import_rijeka_geography.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RijekaGeographyImporter = module.RijekaGeographyImporter


class GeographyValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_duplicate_or_outside_geography_never_writes(self):
        connection = SimpleNamespace(execute=AsyncMock())
        item = {'location_id': '00000000-0000-0000-0000-000000000001',
                'review_status': 'matched', 'review_note': 'Reviewed address point',
                'selected': {'longitude': 14.4, 'latitude': 45.33,
                             'source_url': 'https://www.openstreetmap.org/node/1'}}
        for objects in ([], [item, item], [{**item, 'selected': {**item['selected'], 'latitude': 46.3}}]):
            with self.assertRaises(ValueError):
                await RijekaGeographyImporter(connection).apply({'objects': objects})
        connection.execute.assert_not_awaited()


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class RijekaGeographyDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.context = database_pool(dsn)
        self.pool = await self.context.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction()
        await self.tx.start()
        self.rows = rijeka_records()
        self.repo = AsyncpgSourceRepository(self.c)
        self.importer = RijekaGeographyImporter(self.c)
        await self.repo.import_snapshot(self.snapshot())
        row = await self.c.fetchrow('''SELECT r.source_key,l.id,l.kindergarten_id,l.name,l.address
            FROM izvorni_zapisi r JOIN objekti l ON l.id=r.location_id
            WHERE r.raw_data->>'Vrtić'='Zamet' ''')
        self.item = {'location_id': str(row['id']), 'kindergarten_id': str(row['kindergarten_id']),
                     'source_key': row['source_key'], 'location_name': row['name'], 'address': row['address'],
                     'review_status': 'matched', 'review_note': 'Synthetic reviewed address point.',
                     'selected': {'longitude': 14.4, 'latitude': 45.33, 'suburb': 'Test area',
                                  'source_url': 'https://www.openstreetmap.org/node/1',
                                  'match_basis': 'address_point'}}
        self.data = {'objects': [self.item], 'fetched_at': datetime.now(timezone.utc).isoformat(),
                     'licence': 'ODbL 1.0', 'attribution': '© OpenStreetMap contributors'}

    def snapshot(self):
        return SourceSnapshot(rijeka_source(), normalize_records(self.rows, 'rijeka-kindergartens'),
                              datetime.now(timezone.utc))

    async def asyncTearDown(self):
        await self.tx.rollback()
        await self.pool.release(self.c)
        await self.context.__aexit__(None, None, None)

    async def test_import_and_repeat_preserve_ids_manual_areas_and_csv_contacts(self):
        identities = await self.c.fetch('SELECT id,kindergarten_id FROM objekti ORDER BY id')
        await self.c.execute('''UPDATE objekti SET attributes=$2 WHERE id=$1''',
            UUID(self.item['location_id']),
            {'manual_area': {'quarter': 'Reviewed correction'}, 'phone': '051/000001'})
        self.assertEqual((await self.importer.apply(self.data))['imported'], 1)
        await self.importer.apply(self.data)
        await self.repo.import_snapshot(self.snapshot())
        self.assertEqual(await self.c.fetch('SELECT id,kindergarten_id FROM objekti ORDER BY id'), identities)
        attributes = await self.c.fetchval('SELECT attributes FROM objekti WHERE id=$1',
                                         UUID(self.item['location_id']))
        self.assertEqual(attributes['quarter'], 'Reviewed correction')
        self.assertEqual(attributes['phone'], '051/000001')
        api = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Rijeka'))
        mapped = [row for row in api if row['longitude'] is not None]
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]['longitude'], 14.4)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM odlomci_znanja'), 1)
        self.assertEqual({area for row in api for area in row['areas']},
                         {'Reviewed correction', 'Test area'})

    async def test_address_change_demotes_old_geography_and_requires_new_review(self):
        await self.importer.apply(self.data)
        self.rows[0]['Adresa'] = 'Moved 99'
        await self.repo.import_snapshot(self.snapshot())
        api = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Rijeka'))
        self.assertTrue(all(row['longitude'] is None for row in api))
        self.assertTrue(all(not row['areas'] for row in api))
        self.assertEqual(await self.c.fetchval("SELECT match_status FROM izvorni_zapisi WHERE raw_data ? 'reviewed_address'"),
                         'candidate')
        before = await self.c.fetchval("SELECT fetched_at FROM izvori_podataka WHERE dataset_key='rijeka-reviewed-geography'")
        with self.assertRaises(ValueError):
            async with self.c.transaction():
                await self.importer.apply(self.data)
        self.assertEqual(await self.c.fetchval("SELECT fetched_at FROM izvori_podataka WHERE dataset_key='rijeka-reviewed-geography'"), before)
