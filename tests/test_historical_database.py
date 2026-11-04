"""Rollback-only fixtures protect identity matching and historical evidence scopes."""
import os
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from urllib.parse import urlparse
from dataclasses import replace

from KIDSic.dao.concrete.asyncpg_historical import AsyncpgHistoricalRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.db.database import database_pool
from KIDSic.dto.historical import HistoricalSnapshot
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.source import PlannedSource, SourceSnapshot
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from KIDSic.services.concrete.historical_parser import HistoricalTableParser
from KIDSic.services.concrete.historical import HistoricalService
from KIDSic.exceptions import SourceImportError
from test_sources import MUNICIPAL, source_client
from test_historical import DEFINITIONS, PROGRAMS, municipal_table, package


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class HistoricalDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.context = database_pool(dsn)
        self.pool = await self.context.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction(); await self.tx.start()
        self.directory = AsyncpgSourceRepository(self.c)
        self.history = AsyncpgHistoricalRepository(self.c)
        from KIDSic.dto.source import SourceDefinition
        client = source_client('municipal')
        definition = SourceDefinition('directory', 'https://example.invalid', 'directory', 'municipal')
        source = PlannedSource(definition, client.get_package.return_value, client.get_package.return_value.resources[0])
        rows = normalize_records([MUNICIPAL, {**MUNICIPAL, 'Id': 2, 'Naziv': 'DV Primjer-PO Druga',
                                'Adresa': 'Druga 2', 'TipVrtica': 'Područni'}], 'municipal')
        await self.directory.import_snapshot(SourceSnapshot(source, rows, datetime.now(timezone.utc)))

    async def asyncTearDown(self):
        await self.tx.rollback(); await self.pool.release(self.c)
        await self.context.__aexit__(None, None, None)

    async def snapshot(self, index=0, table=None):
        definition = DEFINITIONS[index]; metadata = package(definition)
        source = PlannedSource(definition.source, metadata, metadata.resources[0])
        await self.directory.register(source)
        rows = HistoricalTableParser().parse(table or (PROGRAMS if index == 0 else municipal_table()), definition)
        return HistoricalSnapshot(source, rows, datetime.now(timezone.utc), definition.reference_date, definition.date_kind)

    async def test_facility_programs_and_institution_counts_keep_separate_scopes(self):
        before = await self.c.fetch('SELECT id,kindergarten_id,address FROM location ORDER BY id')
        await self.history.import_snapshot(await self.snapshot())
        await self.history.import_snapshot(await self.snapshot(1))
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery())
        self.assertEqual(len(rows), 2)
        main = next(r for r in rows if r['address'] == 'Primjer 1')
        branch = next(r for r in rows if r['address'] == 'Druga 2')
        self.assertEqual(len(main['historical_data']), 2)
        self.assertEqual(len(branch['historical_data']), 1)  # slash is not evidence of a program
        self.assertEqual(main['historical_data'][1]['programs'], ['Montessori', 'engleski jezik'])
        self.assertEqual(main['historical_data'][0]['scope'], 'institution')
        self.assertEqual(main['historical_data'][0]['reference_date'], '2025-01-01')
        self.assertEqual(str(await self.c.fetchval("SELECT observed_on FROM data_source WHERE dataset_key='zagreb-vacancies-2025'")), '2025-01-01')
        self.assertIsNone(await self.c.fetchval("SELECT observed_on FROM data_source WHERE dataset_key='zagreb-programs-2019'"))
        self.assertEqual(sum(v['free_places'] for v in main['historical_data'][0]['vacancies']), 5)
        self.assertEqual(await self.c.fetch('SELECT id,kindergarten_id,address FROM location ORDER BY id'), before)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM program'), 0)
        self.assertEqual(await AsyncpgLocationRepository(self.c).list_locations(
            LocationQuery(program='Montessori', age_months=24, include_unknown=False)), [])

    async def test_reimport_activates_one_batch_and_revocation_hides_history(self):
        snapshot = await self.snapshot()
        await self.history.import_snapshot(snapshot)
        await self.history.import_snapshot(snapshot)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM historical_record'), 4)
        repo = AsyncpgLocationRepository(self.c)
        self.assertEqual(sum(len(r['historical_data']) for r in await repo.list_locations(LocationQuery())), 1)
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE dataset_key=$1', snapshot.source.definition.key)
        self.assertTrue(all(not r['historical_data'] for r in await repo.list_locations(LocationQuery())))
        with self.assertRaises(SourceImportError):
            await self.history.import_snapshot(snapshot)

    async def test_unmatched_rows_are_review_candidates_and_failed_batch_keeps_previous(self):
        table = PROGRAMS + [['DV Nepostojeći', 'Nepostojeća 99', 'Gradski vrtić', 'Montessori']]
        result = await self.history.import_snapshot(await self.snapshot(table=table))
        self.assertEqual((result['accepted'], result['needs_review']), (2, 1))
        self.assertEqual(await self.c.fetchval("SELECT count(*) FROM historical_record WHERE match_status='candidate' AND kindergarten_id IS NULL"), 1)
        before = await self.c.fetch('SELECT id,active_batch_id FROM data_source ORDER BY id')
        snapshot = await self.snapshot()
        bad = replace(snapshot, rows=(replace(snapshot.rows[0], name='No match'),))
        with self.assertRaises(SourceImportError):
            async with self.c.transaction():
                await self.history.import_snapshot(bad)
        self.assertEqual(await self.c.fetch('SELECT id,active_batch_id FROM data_source ORDER BY id'), before)

    async def test_provider_conflicts_and_ambiguous_addresses_never_link_automatically(self):
        snapshot = await self.snapshot()
        bad = replace(snapshot.rows[0], source_key='mismatch', provider_kind='private')
        result = await self.history.import_snapshot(replace(snapshot, rows=(snapshot.rows[1], bad)))
        self.assertEqual((result['accepted'], result['needs_review']), (1, 1))
        await self.c.execute('''INSERT INTO location(kindergarten_id,name,address,settlement,settlement_key,municipality_id)
            SELECT kindergarten_id,name,address,settlement,settlement_key,municipality_id FROM location WHERE address='Primjer 1' ''')
        # An unattested duplicate cannot anchor a match; active duplicates are ambiguous.
        await self.c.execute('''INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method)
            SELECT s.id,s.active_batch_id,'{}',l.kindergarten_id,l.id,'accepted','manual' FROM location l,data_source s
            WHERE s.dataset_key='directory' AND NOT EXISTS(SELECT 1 FROM source_record r WHERE r.location_id=l.id)''')
        result = await self.history.import_snapshot(snapshot)
        self.assertEqual((result['accepted'], result['needs_review']), (1, 1))

    async def test_same_name_and_address_outside_zagreb_cannot_anchor_history(self):
        municipality = await self.c.fetchval("INSERT INTO municipality(key,name) VALUES ('rijeka','Rijeka') RETURNING id")
        owner = await self.c.fetchval("INSERT INTO kindergarten(name,provider_kind) VALUES ('DV Primjer','municipal') RETURNING id")
        location = await self.c.fetchval('''INSERT INTO location(kindergarten_id,name,address,settlement,settlement_key,municipality_id)
            VALUES($1,'DV Primjer','Primjer 1','Rijeka','rijeka',$2) RETURNING id''', owner, municipality)
        await self.c.execute('''INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method)
            SELECT id,active_batch_id,'{}',$1,$2,'accepted','manual' FROM data_source WHERE dataset_key='directory' ''', owner, location)
        result = await self.history.import_snapshot(await self.snapshot())
        self.assertEqual(result['accepted'], 2)
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Rijeka'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['historical_data'], [])

    async def test_failure_in_later_source_rolls_back_registration_and_previous_source(self):
        snapshot = await self.snapshot(1)
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE dataset_key=$1', snapshot.source.definition.key)
        before = await self.c.fetch('SELECT id,active_batch_id FROM data_source ORDER BY id')
        definitions = DEFINITIONS[:2]
        clients = {d.source.key: SimpleNamespace(get_package=AsyncMock(return_value=package(d)),
            download_table=AsyncMock(return_value=table)) for d, table in zip(definitions, (PROGRAMS, municipal_table()))}
        @asynccontextmanager
        async def work():
            async with self.c.transaction():
                yield SimpleNamespace(sources=self.directory, historical=self.history)
        with self.assertRaises(SourceImportError):
            await HistoricalService(clients, definitions, work).import_data()
        self.assertEqual(await self.c.fetch('SELECT id,active_batch_id FROM data_source ORDER BY id'), before)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM historical_record'), 0)
