"""Actual asyncpg persistence and transaction tests on a disposable migrated database."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import os
from types import SimpleNamespace
import unittest
from urllib.parse import urlparse
import httpx

from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
from KIDSic.db.database import database_pool
from KIDSic.db.uow.source import AsyncpgSourceUnitOfWork
from KIDSic.config.settings import Settings
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.exceptions import SourceImportError
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from KIDSic.services.concrete.source import SourceService
from test_sources import NATIONAL, MUNICIPAL, source_client


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class SourceDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use kidsic_test_* database')
        self.context = database_pool(dsn)
        self.pool = await self.context.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction()
        await self.tx.start()
        self.repo = AsyncpgSourceRepository(self.c)
        self.client = source_client()
        self.definition = SourceDefinition('national', 'https://data.gov.hr/ckan', 'djecji-vrtici', 'national')
        self.source = PlannedSource(self.definition, self.client.get_package.return_value,
                                    self.client.get_package.return_value.resources[0])

    async def asyncTearDown(self):
        await self.tx.rollback()
        await self.pool.release(self.c)
        await self.context.__aexit__(None, None, None)

    def snapshot(self, records=None, source=None, parser='national'):
        return SourceSnapshot(source or self.source, normalize_records(records or [NATIONAL], parser),
                              datetime.now(timezone.utc))

    async def test_childminder_csv_import_preserves_identity_and_last_good_snapshot(self):
        fixtures = Path(__file__).parent / 'fixtures'
        package = json.loads((fixtures / 'ckan_childminders.json').read_text())
        state = {'bad': False, 'moved': False}

        def respond(request):
            if request.url.path.endswith('package_show'):
                return httpx.Response(200, json=package)
            body = (fixtures / 'varazdin_childminders.csv').read_bytes()
            if state['bad']:
                body = b'wrong;columns\n1;2'
            elif state['moved']:
                body = body.replace(b'Primjer 1,', b'Primjer 99,')
            return httpx.Response(200, content=body)

        @asynccontextmanager
        async def work():
            async with self.c.transaction():
                yield SimpleNamespace(sources=self.repo)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            service = SourceServiceFactory(Settings(database_url=os.environ['KIDSIC_TEST_DATABASE_URL'])).create(
                http, work, source_keys=['varazdin-childminders'])
            first = await service.import_data()
            self.assertEqual(first['records'], 2)
            self.assertEqual(first['sources'][0]['accepted'], 2)
            identities = await self.c.fetch('SELECT id,oib FROM kindergarten ORDER BY name')
            state['moved'] = True
            second = await service.import_data()
            self.assertEqual(second['sources'][0]['kindergartens_added'], 0)
            self.assertEqual(await self.c.fetch('SELECT id,oib FROM kindergarten ORDER BY name'), identities)
            self.assertEqual(await self.c.fetchval('SELECT count(*) FROM location'), 0)
            self.assertEqual(await self.c.fetchval('SELECT count(*) FROM knowledge_chunk'), 0)
            self.assertEqual(await self.c.fetchval("SELECT count(*) FROM kindergarten WHERE provider_kind='childminder'"), 2)
            self.assertEqual(await self.c.fetchval("SELECT seat_address FROM kindergarten WHERE oib='00123456789'"), 'Primjer 99')
            rows = await AsyncpgKindergartenRepository(self.c).find_options(city='varazdin', age_months=24, include_unknown=True)
            self.assertEqual({row['scope'] for row in rows}, {'seat'})
            self.assertEqual({row['age_status'] for row in rows}, {'unknown'})
            before = await self.c.fetchval("SELECT active_batch_id FROM data_source WHERE dataset_key='varazdin-childminders'")
            state['bad'] = True
            with self.assertRaises(SourceImportError):
                await service.import_data()
            self.assertEqual(await self.c.fetchval("SELECT active_batch_id FROM data_source WHERE dataset_key='varazdin-childminders'"), before)
            self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 4)

    async def test_registration_is_idempotent_and_preserves_approval_and_active_snapshot(self):
        self.assertEqual(await self.repo.register(self.source), 'added')
        self.assertEqual(await self.repo.register(self.source), 'unchanged')
        await self.repo.import_snapshot(self.snapshot())
        await self.c.execute("UPDATE data_source SET import_allowed=false WHERE dataset_key='national'")
        before = dict(await self.c.fetchrow("SELECT * FROM data_source WHERE dataset_key='national'"))
        changed = PlannedSource(self.definition, self.source.package.model_copy(update={'title': 'New title'}),
                                self.source.resource)
        self.assertEqual(await self.repo.register(changed), 'updated')
        after = await self.c.fetchrow("SELECT * FROM data_source WHERE dataset_key='national'")
        for key in ('import_allowed', 'active_batch_id', 'fetched_at'):
            self.assertEqual(after[key], before[key])
        with self.assertRaises(SourceImportError):
            await self.repo.import_snapshot(self.snapshot())

    async def test_resource_identity_and_url_cannot_be_registered_under_another_source(self):
        await self.repo.register(self.source)
        other_definition = SourceDefinition('other-key', self.definition.base_url,
                                             self.definition.dataset_id, 'national')
        duplicate = PlannedSource(other_definition, self.source.package, self.source.resource)
        with self.assertRaises(SourceImportError):
            await self.repo.register(duplicate)
        changed_id = PlannedSource(other_definition, self.source.package,
                                   self.source.resource.model_copy(update={'id': 'replacement-id'}))
        with self.assertRaises(SourceImportError):
            await self.repo.register(changed_id)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM data_source'), 1)

    async def test_repeated_import_preserves_ids_raw_evidence_and_unknown_age(self):
        first = await self.repo.import_snapshot(self.snapshot())
        identity = await self.c.fetchval('SELECT id FROM kindergarten')
        second = await self.repo.import_snapshot(self.snapshot([{**NATIONAL, 'Telefon': '123'}]))
        # The national directory describes institutions: its address is a seat, not an object.
        self.assertEqual((first['locations_added'], second['locations_added']), (0, 0))
        self.assertEqual(second['kindergartens_added'], 0)
        self.assertEqual(await self.c.fetchval('SELECT id FROM kindergarten'), identity)
        seat = await self.c.fetchrow('SELECT seat_address,seat_settlement,seat_postal_code,m.key '
                                     'FROM kindergarten k JOIN municipality m ON m.id=k.seat_municipality_id')
        self.assertEqual(tuple(seat), ('Primjer 1', 'Varaždin', '42000', 'varazdin'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM location'), 0)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 2)
        self.assertEqual([r['match_method'] for r in await self.c.fetch(
            'SELECT match_method FROM source_record ORDER BY fetched_at')], ['new', 'source_identity'])
        self.assertEqual(await self.c.fetchval('SELECT phone FROM kindergarten'), '123')
        raw = await self.c.fetchval('SELECT raw_data FROM source_record WHERE batch_id=$1::text::uuid',
                                     second['batch_id'])
        self.assertEqual(raw['Telefon'], '123')
        search = AsyncpgKindergartenRepository(self.c)
        result = await search.find_options(city='varazdina', age_months=24, include_unknown=True)
        self.assertEqual((result[0]['age_status'], result[0]['scope']), ('unknown', 'seat'))
        self.assertEqual(await search.find_options(city='varazdin', age_months=24), [])
        self.assertIsNone(await self.c.fetchval('SELECT observed_on FROM data_source'))

    def municipal_source(self):
        client = source_client('municipal')
        return PlannedSource(SourceDefinition('zagreb-municipal', 'https://data.zagreb.hr',
                             'gradski_vrtici_grada_zagreba', 'municipal'),
                             client.get_package.return_value, client.get_package.return_value.resources[0])

    async def test_city_objects_share_owner_and_link_to_national_record(self):
        await self.repo.import_snapshot(self.snapshot([{**NATIONAL, 'Mjesto': 'Zagreb',
                                                         'Zupanija': 'Grad Zagreb'}]))
        branch = {**MUNICIPAL, 'Id': 2, 'Naziv': 'DV Primjer-PO Druga',
                  'Adresa': 'Druga 2', 'TipVrtica': 'Područni'}
        await self.repo.import_snapshot(self.snapshot([MUNICIPAL, branch], self.municipal_source(), 'municipal'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 1)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM location'), 2)
        self.assertEqual(await self.c.fetchval('SELECT count(DISTINCT source_id) FROM source_record'), 2)
        self.assertEqual(await self.c.fetchval("SELECT count(*) FROM location WHERE kind='branch'"), 1)
        self.assertEqual([r['match_method'] for r in await self.c.fetch(
            "SELECT match_method FROM source_record WHERE location_id IS NOT NULL ORDER BY source_key")],
            ['name', 'name'])
        rows = await AsyncpgKindergartenRepository(self.c).find_options(
            city='zagreb', age_months=24, include_unknown=True)
        self.assertEqual({r['scope'] for r in rows}, {'location'})

    async def test_zagreb_settlement_suffix_links_to_national_settlement(self):
        await self.repo.import_snapshot(self.snapshot([{**NATIONAL, 'Mjesto': 'Sesvete',
                                                         'Adresa': 'Sjedište 3', 'Zupanija': 'Grad Zagreb'}]))
        main = {**MUNICIPAL, 'Adresa': 'Ive Tijardovića 9, Sesvete'}
        await self.repo.import_snapshot(self.snapshot([main], self.municipal_source(), 'municipal'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 1)
        location = await self.c.fetchrow('SELECT settlement,address,m.key FROM location l '
                                         'JOIN municipality m ON m.id=l.municipality_id')
        self.assertEqual(tuple(location), ('Sesvete', 'Ive Tijardovića 9', 'zagreb'))
        search = AsyncpgKindergartenRepository(self.c)
        for city in ('zagreba', 'sesvete'):
            self.assertEqual(len(await search.find_options(city=city, age_months=24, include_unknown=True)), 1)

    async def test_oib_links_institution_despite_different_name(self):
        from dataclasses import replace
        rows = normalize_records([NATIONAL], 'national')
        await self.repo.import_snapshot(SourceSnapshot(self.source, (replace(rows[0], oib='12345678901'),),
                                                       datetime.now(timezone.utc)))
        renamed = replace(normalize_records([{**NATIONAL, 'Naziv': 'Drugi naziv'}], 'national')[0],
                          oib='12345678901')
        await self.repo.import_snapshot(SourceSnapshot(self.source, (renamed,), datetime.now(timezone.utc)))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 1)
        self.assertEqual(await self.c.fetchval(
            'SELECT match_method FROM source_record ORDER BY fetched_at DESC LIMIT 1'), 'oib')

    async def test_new_snapshot_hides_removed_location_and_keeps_history(self):
        other = {**NATIONAL, 'Naziv': 'Dječji vrtić Drugi', 'Adresa': 'Druga 2'}
        await self.repo.import_snapshot(self.snapshot([NATIONAL, other]))
        await self.repo.import_snapshot(self.snapshot())
        result = await AsyncpgKindergartenRepository(self.c).find_options(
            city='varazdin', age_months=24, include_unknown=True)
        self.assertEqual([r['name'] for r in result], [NATIONAL['Naziv']])
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 3)

    async def test_ambiguous_match_is_retained_for_review(self):
        for name in ('DV Primjer', 'Dječji vrtić "Primjer"'):
            owner = await self.c.fetchval('INSERT INTO kindergarten(name) VALUES ($1) RETURNING id', name)
            await self.c.execute("INSERT INTO location(kindergarten_id,name,settlement,settlement_key,address) "
                                 "VALUES ($1,$2,'Varaždin','varazdin','Primjer 1')", owner, name)
        second = {**NATIONAL, 'Naziv': 'DV Drugi', 'Adresa': 'Druga 2'}
        result = await self.repo.import_snapshot(self.snapshot([NATIONAL, second]))
        self.assertEqual(result['needs_review'], 1)
        self.assertEqual(await self.c.fetchval("SELECT count(*) FROM source_record WHERE match_status='candidate'"), 1)

    async def test_later_failure_rolls_back_all_sources_in_service_transaction(self):
        @asynccontextmanager
        async def work():
            async with self.c.transaction():
                yield SimpleNamespace(sources=self.repo)

        second_client = source_client('municipal')
        second_client.download_records.return_value = [MUNICIPAL]
        second_definition = SourceDefinition('zagreb-municipal', 'https://data.zagreb.hr',
                                             'gradski_vrtici_grada_zagreba', 'municipal')
        second_source = PlannedSource(second_definition, second_client.get_package.return_value,
                                      second_client.get_package.return_value.resources[0])
        await self.repo.register(second_source)
        await self.c.execute("UPDATE data_source SET import_allowed=false WHERE dataset_key='zagreb-municipal'")
        service = SourceService({'national': self.client, 'zagreb-municipal': second_client},
                                [self.definition, second_definition], work)
        with self.assertRaises(SourceImportError):
            await service.import_data()
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 0)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 0)
        self.assertEqual(await self.c.fetchval("SELECT count(*) FROM data_source WHERE dataset_key='national'"), 0)

    async def test_writer_unit_of_work_rolls_back_and_releases_connection(self):
        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
            async with AsyncpgSourceUnitOfWork(self.pool) as work:
                await work.sources.register(self.source)
                raise RuntimeError('synthetic failure')
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM data_source'), 0)

    @unittest.skipUnless(os.getenv('KIDSIC_CKAN_SIMULATION_URL'), 'Start the CKAN Postman simulation')
    async def test_full_http_to_database_path_preserves_snapshot_on_download_failure(self):
        @asynccontextmanager
        async def work():
            async with self.c.transaction():
                yield SimpleNamespace(sources=self.repo)

        url = os.environ['KIDSIC_CKAN_SIMULATION_URL']
        settings = Settings(database_url=os.environ['KIDSIC_TEST_DATABASE_URL'],
                            ckan_base_url=url, ckan_zagreb_base_url=url)
        async with httpx.AsyncClient() as http:
            result = await SourceServiceFactory(settings).create(http, work, source_keys=['national', 'zagreb-municipal', 'zagreb-other']).import_data()
            self.assertEqual(result['records'], 4)
            self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 2)
            self.assertEqual(await self.c.fetchval('SELECT count(*) FROM location'), 3)
            before = await self.c.fetch('SELECT dataset_key,active_batch_id FROM data_source ORDER BY dataset_key')
            broken = Settings(database_url=settings.database_url, ckan_base_url=url,
                              ckan_zagreb_base_url=url, ckan_zagreb_other_dataset_id='broken-download')
            from KIDSic.exceptions import CkanHttpError
            with self.assertRaises(CkanHttpError):
                await SourceServiceFactory(broken).create(http, work, source_keys=['national', 'zagreb-municipal', 'zagreb-other']).import_data()
            self.assertEqual(await self.c.fetch('SELECT dataset_key,active_batch_id FROM data_source ORDER BY dataset_key'),
                             before)
