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
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dto.location import LocationQuery
from KIDSic.db.database import database_pool
from KIDSic.db.uow.asyncpg_source import AsyncpgSourceUnitOfWork
from KIDSic.config.settings import Settings
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.exceptions import SourceImportError, PersistenceError
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

    async def test_city_scope_filters_reimports_and_rejects_unfiltered_snapshots(self):
        from dataclasses import replace
        records = [{**NATIONAL, 'Mjesto': city, 'Zupanija': county} for city, county in (
            ('Zagreb', 'Grad Zagreb'), ('Varaždin', 'Varaždinska županija'),
            ('Rijeka', 'Primorsko-goranska županija'), ('Split', 'Splitsko-dalmatinska županija'))]
        snapshot = self.snapshot(records)
        await self.repo.import_snapshot(snapshot)
        identities = await self.c.fetch('SELECT k.id,ks.settlement AS seat_settlement FROM kindergarten k LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id ORDER BY k.id')
        self.assertEqual({r['seat_settlement'] for r in identities}, {'Zagreb', 'Varaždin', 'Rijeka'})
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 3)
        await self.repo.import_snapshot(self.snapshot(records))
        self.assertEqual(await self.c.fetch('SELECT k.id,ks.settlement AS seat_settlement FROM kindergarten k LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id ORDER BY k.id'), identities)
        bad = replace(snapshot, rows=(replace(snapshot.rows[0], municipality='split'),))
        with self.assertRaises(SourceImportError):
            await self.repo.import_snapshot(bad)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 3)

    async def test_city_cleanup_preserves_supported_branches_and_removes_dependent_data(self):
        await self.c.execute('ALTER TABLE kindergarten ADD COLUMN seat_settlement text, ADD COLUMN seat_settlement_key text, ADD COLUMN seat_municipality_id uuid REFERENCES municipality(id)')
        legacy = (Path(__file__).resolve().parents[1] / 'src/KIDSic/db/alembic/versions/0001_simple_rag.sql').read_text()
        for sql in legacy.split('\n-- statement\n'):
            if sql.startswith(('CREATE TABLE program', 'CREATE INDEX ix_program')):
                await self.c.execute(sql)
        await self.c.execute('ALTER TABLE knowledge_chunk ADD COLUMN program_id uuid')
        await self.c.execute('ALTER TABLE enrolment ADD COLUMN municipality_id uuid REFERENCES municipality(id)')
        from uuid import uuid4
        await self.repo.register(self.source)
        source_id = await self.c.fetchval("SELECT id FROM data_source WHERE dataset_key='national'")
        batch = uuid4()
        await self.c.execute('UPDATE data_source SET active_batch_id=$2 WHERE id=$1', source_id, batch)
        cities = {city: await self.c.fetchval('INSERT INTO municipality(key,name) VALUES ($1,$1) '
                  'RETURNING id', city) for city in ('zagreb', 'varazdin', 'rijeka', 'split', 'osijek')}

        async def place(name, city, *, owner=None, settlement=None):
            if owner is None:
                owner = await self.c.fetchval('''INSERT INTO kindergarten
                    (name,seat_settlement,seat_settlement_key,seat_municipality_id)
                    VALUES ($1,$2,$2,$3) RETURNING id''', name, city, cities[city])
            location = await self.c.fetchval('''INSERT INTO location
                (kindergarten_id,name,settlement,settlement_key,municipality_id)
                VALUES ($1,$2,$3,$3,$4) RETURNING id''', owner, name, settlement or city, cities[city])
            record = await self.c.fetchval('''INSERT INTO source_record
                (source_id,batch_id,raw_data,kindergarten_id,location_id,match_status,match_method)
                VALUES ($1,$2,'{}',$3,$4,'accepted','manual') RETURNING id''',
                source_id, batch, owner, location)
            program = await self.c.fetchval('''INSERT INTO program
                (kindergarten_id,location_id,source_record_id,name,verified_on)
                VALUES ($1,$2,$3,'Synthetic',CURRENT_DATE) RETURNING id''', owner, location, record)
            await self.c.execute('''INSERT INTO enrolment
                (kindergarten_id,source_record_id,academic_year,application_url,channel)
                VALUES ($1,$2,'2026/27','https://example.invalid','kindergarten')''', owner, record)
            await self.c.execute('''INSERT INTO knowledge_chunk
                (kindergarten_id,location_id,source_record_id,program_id,ordinal,content,source_url,content_sha256)
                VALUES ($1,$2,$3,$4,0,'Synthetic','https://example.invalid',$5)''',
                owner, location, record, program, 'a' * 64)
            return owner, location, record

        outside = await place('Outside only', 'split')
        rijeka = await place('Rijeka retained', 'rijeka')
        external = await place('External seat', 'split')
        zagreb = await place('Zagreb branch', 'zagreb', owner=external[0], settlement='sesvete')
        varazdin = await place('Varaždin retained', 'varazdin')
        for city, county in (('Split', 'Splitsko-dalmatinska županija'), ('Sesvete', 'Grad Zagreb')):
            await self.c.execute('''INSERT INTO source_record(source_id,batch_id,raw_data)
                VALUES ($1,$2,$3)''', source_id, batch, {**NATIONAL, 'Mjesto': city, 'Zupanija': county})
        await self.c.execute('''INSERT INTO enrolment
            (municipality_id,source_record_id,academic_year,application_url,channel)
            VALUES ($1,$2,'2026/27','https://example.invalid','city_system')''', cities['split'], rijeka[2])

        await self.c.execute('CREATE TEMP TABLE availability (source_record_id uuid, kindergarten_id uuid, location_id uuid, program_id uuid)')
        migration = (Path(__file__).resolve().parents[1] /
                     'src/KIDSic/db/alembic/versions/0005_supported_cities.sql').read_text()
        await self.c.execute(migration)
        self.assertEqual({r['id'] for r in await self.c.fetch('SELECT id FROM kindergarten')},
                         {rijeka[0], external[0], varazdin[0]})
        self.assertEqual({r['id'] for r in await self.c.fetch('SELECT id FROM location')},
                         {rijeka[1], zagreb[1], varazdin[1]})
        for table in ('program', 'enrolment', 'knowledge_chunk'):
            self.assertEqual(await self.c.fetchval(f'SELECT count(*) FROM {table}'), 3, table)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 4)
        self.assertIsNone(await self.c.fetchval("SELECT id FROM municipality WHERE key='osijek'"))
        self.assertEqual(await self.c.fetchval('SELECT active_batch_id FROM data_source WHERE id=$1', source_id), batch)
        await self.c.execute(migration)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 3)

    async def test_provider_types_survive_reimport_and_are_exposed_with_their_source(self):
        from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
        from KIDSic.dto.location import LocationQuery
        records = [{**NATIONAL, 'Naziv': name} for name in
                   ('DV Varaždin', 'DV Bajka', 'DV Sveta Uršula')]
        await self.repo.import_snapshot(self.snapshot(records))
        identities = await self.c.fetch('SELECT id,provider_kind FROM kindergarten ORDER BY name')
        await self.repo.import_snapshot(self.snapshot(records))
        self.assertEqual(await self.c.fetch(
            'SELECT id,provider_kind FROM kindergarten ORDER BY name'), identities)
        locations = AsyncpgLocationRepository(self.c)
        for kind in ('municipal', 'private', 'religious'):
            rows = await locations.list_locations(LocationQuery(city='Varaždin', provider_kind=kind))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['provider_kind'], kind)
            self.assertIn('provider_kind', rows[0]['field_sources'])
            self.assertEqual(await self.c.fetchval("SELECT provenance->'provider_kind'->>'source_url' "
                'FROM kindergarten WHERE id=$1', rows[0]['kindergarten_id']),
                'https://varazdin.hr/djecji-vrtici/')
        options = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='varazdin'))
        self.assertEqual({row['provider_kind'] for row in options},
                         {'municipal', 'private', 'religious'})

    async def test_provider_backfill_preserves_known_types_and_other_cities(self):
        records = [{**NATIONAL, 'Naziv': 'DV Bajka'},
                   {**NATIONAL, 'Naziv': 'DV Varaždin'},
                   {**NATIONAL, 'Naziv': 'Udruga Primjer', 'Mjesto': 'Zagreb',
                    'Zupanija': 'Grad Zagreb'}]
        await self.repo.import_snapshot(self.snapshot(records))
        await self.c.execute('ALTER TABLE kindergarten ADD COLUMN seat_settlement text, ADD COLUMN seat_settlement_key text, ADD COLUMN seat_municipality_id uuid, ADD COLUMN seat_county text')
        await self.c.execute('UPDATE kindergarten k SET seat_settlement=ks.settlement,seat_settlement_key=ks.settlement_key,seat_municipality_id=ks.municipality_id,seat_county=m.county FROM kindergarten_seat ks LEFT JOIN municipality m ON m.id=ks.municipality_id WHERE k.id=ks.kindergarten_id')
        # Simulate a legacy row without passing through the now city-limited import.
        await self.c.execute("INSERT INTO kindergarten(name,seat_settlement,seat_settlement_key) "
                             "VALUES ('DV Bajka','Drugi grad','drugi grad')")
        await self.c.execute("UPDATE kindergarten SET provider_kind='unknown'")
        await self.c.execute("UPDATE kindergarten SET provider_kind='private' WHERE name='DV Varaždin'")
        before = await self.c.fetch('SELECT id,name,seat_settlement,provider_kind,provenance '
                                    'FROM kindergarten ORDER BY id')
        migration = (Path(__file__).resolve().parents[1] / 'src/KIDSic/db/alembic/versions/'
                     '0004_provider_kinds.sql').read_text()
        await self.c.execute(migration)
        rows = await self.c.fetch('SELECT id,name,seat_settlement,provider_kind,provenance '
                                  'FROM kindergarten ORDER BY id')
        self.assertEqual({(r['name'], r['seat_settlement']): r['provider_kind'] for r in rows}, {
            ('DV Bajka', 'Varaždin'): 'private', ('DV Varaždin', 'Varaždin'): 'private',
            ('DV Bajka', 'Drugi grad'): 'unknown', ('Udruga Primjer', 'Zagreb'): 'other'})
        await self.c.execute(migration)
        self.assertEqual(await self.c.fetch('SELECT id,name,seat_settlement,provider_kind,provenance '
                                            'FROM kindergarten ORDER BY id'), rows)
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('provider_migration',
            Path(__file__).resolve().parents[1] / 'src/KIDSic/db/alembic/versions/'
            '0004_provider_kinds.py')
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)
        with patch.object(revision.op, 'execute') as execute:
            revision.downgrade()
        await self.c.execute(execute.call_args.args[0])
        self.assertEqual(await self.c.fetch('SELECT id,name,seat_settlement,provider_kind,provenance '
                                            'FROM kindergarten ORDER BY id'), before)

    async def test_database_rejects_missing_or_invalid_provider_kind(self):
        import asyncpg
        for kind, error in ((None, asyncpg.NotNullViolationError),
                            ('invalid', asyncpg.CheckViolationError)):
            with self.subTest(kind=kind):
                with self.assertRaises(error):
                    async with self.c.transaction():
                        await self.c.execute('INSERT INTO kindergarten(name,provider_kind) '
                                             "VALUES ('Synthetic',$1)", kind)

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
            self.assertEqual(await self.c.fetchval("SELECT ks.address FROM kindergarten k JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id WHERE k.oib='00123456789'"), 'Primjer 99')
            rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='varazdin'))
            self.assertEqual({row['location_role'] for row in rows}, {'seat'})
            before = await self.c.fetchval("SELECT active_batch_id FROM data_source WHERE dataset_key='varazdin-childminders'")
            state['bad'] = True
            with self.assertRaises(SourceImportError):
                await service.import_data()
            self.assertEqual(await self.c.fetchval("SELECT active_batch_id FROM data_source WHERE dataset_key='varazdin-childminders'"), before)
            self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 2)

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
        record_identity = await self.c.fetchval('SELECT id FROM source_record')
        second = await self.repo.import_snapshot(self.snapshot([{**NATIONAL, 'Telefon': '123'}]))
        # The national directory describes institutions: its address is a seat, not an object.
        self.assertEqual((first['locations_added'], second['locations_added']), (0, 0))
        self.assertEqual(second['kindergartens_added'], 0)
        self.assertEqual(await self.c.fetchval('SELECT id FROM source_record'), record_identity)
        self.assertEqual(await self.c.fetchval('SELECT id FROM kindergarten'), identity)
        seat = await self.c.fetchrow('SELECT ks.address,ks.settlement,ks.postal_code,m.key '
                                     'FROM kindergarten k JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id JOIN municipality m ON m.id=ks.municipality_id')
        self.assertEqual(tuple(seat), ('Primjer 1', 'Varaždin', '42000', 'varazdin'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM location'), 0)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 1)
        self.assertEqual([r['match_method'] for r in await self.c.fetch(
            'SELECT match_method FROM source_record ORDER BY fetched_at')], ['new'])
        self.assertEqual(await self.c.fetchval('SELECT phone FROM kindergarten'), '123')
        raw = await self.c.fetchval('SELECT raw_data FROM source_record WHERE batch_id=$1::text::uuid',
                                     second['batch_id'])
        self.assertEqual(raw['Telefon'], '123')
        search = AsyncpgLocationRepository(self.c)
        result = await search.list_locations(LocationQuery(city='varazdina'))
        self.assertEqual(result[0]['location_role'], 'seat')
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
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='zagreb'))
        self.assertEqual({r['location_role'] for r in rows}, {'facility'})

    async def test_rijeka_csv_links_national_parents_preserves_contacts_and_reimports(self):
        from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
        from KIDSic.dto.location import LocationQuery
        from test_rijeka import rijeka_records, rijeka_source
        records = rijeka_records()
        parents = ['Dječji vrtić Rijeka', 'Dječji vrtić "Mala Vila", waldorfski',
                   'Dječji vrtić "Nazaret"', 'Dječji vrtić "Pinokio"']
        national = [{**NATIONAL, 'Naziv': name, 'Mjesto': 'Rijeka',
                     'Zupanija': 'Primorsko-goranska županija', 'Adresa': f'Sjedište {i}',
                     'Telefon': '051/000001', 'ePosta': 'test@example.invalid'}
                    for i, name in enumerate(parents)]
        await self.repo.import_snapshot(self.snapshot(national))
        owners = await self.c.fetch('SELECT k.id,k.name,ks.address AS seat_address FROM kindergarten k LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id ORDER BY k.id')
        source = rijeka_source()
        first = await self.repo.import_snapshot(self.snapshot(records, source, 'rijeka-kindergartens'))
        self.assertEqual((first['accepted'], first['kindergartens_added'], first['locations_added']), (8, 0, 8))
        self.assertEqual(await self.c.fetch('SELECT k.id,k.name,ks.address AS seat_address FROM kindergarten k LEFT JOIN kindergarten_seat ks ON ks.kindergarten_id=k.id ORDER BY k.id'), owners)
        locations = await self.c.fetch('SELECT id,kindergarten_id FROM location ORDER BY id')
        api = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Rijeka'))
        self.assertEqual(len(api), 8)
        self.assertEqual({r['phone'] for r in api}, {'051/000001'})
        self.assertEqual({r['location_role'] for r in api}, {'facility'})
        self.assertTrue(all(r['longitude'] is None and r['latitude'] is None for r in api))
        self.assertEqual({r['provider_kind'] for r in api}, {'municipal', 'private', 'religious'})
        self.assertTrue(all(r['sources'] and r['field_sources'].get('address') for r in api))
        changed = [{**r, 'RBR': str(i + 100)} for i, r in enumerate(reversed(records))]
        changed[-1]['Adresa'] = 'Nova adresa 99'
        second = await self.repo.import_snapshot(self.snapshot(changed, source, 'rijeka-kindergartens'))
        self.assertEqual((second['kindergartens_added'], second['locations_added']), (0, 0))
        self.assertEqual(await self.c.fetch('SELECT id,kindergarten_id FROM location ORDER BY id'), locations)
        self.assertEqual(await self.c.fetchval("SELECT count(*) FROM location WHERE address='Nova adresa 99'"), 1)
        # The national refresh must preserve the facility category and parent identity.
        await self.repo.import_snapshot(self.snapshot(national))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 4)
        self.assertEqual(await self.c.fetchval("SELECT count(*) FROM kindergarten WHERE provider_kind='unknown'"), 0)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 12)

    async def test_rijeka_csv_can_precede_national_import_without_duplicate_parents(self):
        from test_rijeka import rijeka_records, rijeka_source
        records = rijeka_records()
        await self.repo.import_snapshot(self.snapshot(records, rijeka_source(), 'rijeka-kindergartens'))
        owners = await self.c.fetch('SELECT id FROM kindergarten ORDER BY id')
        self.assertEqual(len(owners), 4)
        national = [{**NATIONAL, 'Naziv': name, 'Mjesto': 'Rijeka',
                     'Zupanija': 'Primorsko-goranska županija'} for name in (
                         'Dječji vrtić Rijeka', 'Dječji vrtić "Mala Vila", waldorfski',
                         'Dječji vrtić Nazaret', 'Dječji vrtić Pinokio')]
        result = await self.repo.import_snapshot(self.snapshot(national))
        self.assertEqual(result['kindergartens_added'], 0)
        self.assertEqual(await self.c.fetch('SELECT id FROM kindergarten ORDER BY id'), owners)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM location'), 8)

    async def test_zagreb_settlement_suffix_links_to_national_settlement(self):
        await self.repo.import_snapshot(self.snapshot([{**NATIONAL, 'Mjesto': 'Sesvete',
                                                         'Adresa': 'Sjedište 3', 'Zupanija': 'Grad Zagreb'}]))
        main = {**MUNICIPAL, 'Adresa': 'Ive Tijardovića 9, Sesvete'}
        await self.repo.import_snapshot(self.snapshot([main], self.municipal_source(), 'municipal'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 1)
        location = await self.c.fetchrow('SELECT settlement,address,m.key FROM location l '
                                         'JOIN municipality m ON m.id=l.municipality_id')
        self.assertEqual(tuple(location), ('Sesvete', 'Ive Tijardovića 9', 'zagreb'))
        search = AsyncpgLocationRepository(self.c)
        for city in ('zagreba',):
            self.assertEqual(len(await search.list_locations(LocationQuery(city=city))), 1)

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

    async def test_new_snapshot_removes_missing_records(self):
        other = {**NATIONAL, 'Naziv': 'Dječji vrtić Drugi', 'Adresa': 'Druga 2'}
        await self.repo.import_snapshot(self.snapshot([NATIONAL, other]))
        await self.repo.import_snapshot(self.snapshot())
        result = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='varazdin'))
        self.assertEqual([r['name'] for r in result], [NATIONAL['Naziv']])
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 1)

    async def test_current_state_rejects_invalid_sets_atomically_and_keeps_manual_decisions(self):
        from dataclasses import replace
        await self.repo.import_snapshot(self.snapshot())
        before = await self.c.fetch('SELECT * FROM source_record')
        original = self.snapshot()
        for rows in ((), (original.rows[0], original.rows[0])):
            with self.assertRaises(SourceImportError):
                await self.repo.import_snapshot(replace(original, rows=rows))
            self.assertEqual(await self.c.fetch('SELECT * FROM source_record'), before)
        await self.c.execute("UPDATE source_record SET match_method='manual',match_note='Reviewed owner'")
        identity = before[0]['id']
        await self.repo.import_snapshot(self.snapshot())
        record = await self.c.fetchrow('SELECT * FROM source_record')
        self.assertEqual((record['id'], record['match_method'], record['match_note']),
                         (identity, 'manual', 'Reviewed owner'))

    async def test_current_state_clears_own_missing_contact_and_preserves_other_sources(self):
        from dataclasses import replace
        original = self.snapshot()
        original = replace(original, rows=(replace(original.rows[0], phone='old'),))
        await self.repo.import_snapshot(original)
        await self.repo.import_snapshot(replace(original, rows=(replace(original.rows[0], phone=None),)))
        self.assertIsNone(await self.c.fetchval('SELECT phone FROM kindergarten'))
        owner = await self.c.fetchval('SELECT id FROM kindergarten')
        await self.c.execute("UPDATE kindergarten SET phone='reviewed',provenance=provenance || $2 WHERE id=$1",
                             owner, {'phone': {'dataset_key': 'another-reviewed-source'}})
        await self.repo.import_snapshot(original)
        self.assertEqual(await self.c.fetchval('SELECT phone FROM kindergarten'), 'reviewed')
        await self.c.execute("UPDATE kindergarten SET provider_kind='private'")
        before = await self.c.fetch('SELECT * FROM source_record')
        with self.assertRaisesRegex(SourceImportError, 'provider_kind'):
            await self.repo.import_snapshot(replace(original, rows=(replace(original.rows[0], provider_kind='unknown'),)))
        self.assertEqual(await self.c.fetch('SELECT * FROM source_record'), before)
        await self.c.execute("UPDATE kindergarten SET provenance=jsonb_set(provenance,'{provider_kind}',(provenance->'provider_kind')-'dataset_key')")
        with self.assertRaisesRegex(SourceImportError, 'provider_kind'):
            await self.repo.import_snapshot(replace(original, rows=(replace(original.rows[0], provider_kind='unknown'),)))
        self.assertEqual(await self.c.fetch('SELECT * FROM source_record'), before)

    async def test_removed_state_deletes_derived_rows_and_dangling_provenance(self):
        second = {**NATIONAL, 'Naziv': 'DV Drugi', 'Adresa': 'Druga 2'}
        await self.repo.import_snapshot(self.snapshot([NATIONAL, second]))
        record = await self.c.fetchrow("SELECT * FROM source_record WHERE raw_data->>'Naziv'='DV Drugi'")
        await self.c.execute("INSERT INTO knowledge_chunk(kindergarten_id,source_record_id,ordinal,content,source_url,content_sha256) VALUES ($1,$2,0,'Test','https://example.invalid',$3)", record['kindergarten_id'], record['id'], 'a'*64)
        await self.c.execute("INSERT INTO enrolment(kindergarten_id,source_record_id,academic_year,application_url,channel) VALUES ($1,$2,'2026/27','https://example.invalid','kindergarten')", record['kindergarten_id'], record['id'])
        await self.repo.import_snapshot(self.snapshot())
        for table in ('knowledge_chunk', 'enrolment'):
            self.assertEqual(await self.c.fetchval(f'SELECT count(*) FROM {table}'), 0)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM source_record'), 1)
        self.assertEqual(await self.c.fetchval('SELECT provenance FROM kindergarten WHERE id=$1', record['kindergarten_id']), {})

    async def test_seat_migration_rejects_county_disagreements(self):
        import asyncpg
        await self.repo.import_snapshot(self.snapshot())
        await self.c.execute('ALTER TABLE kindergarten ADD COLUMN seat_county text, ADD COLUMN seat_municipality_id uuid')
        await self.c.execute('ALTER TABLE location ADD COLUMN county text')
        await self.c.execute("UPDATE kindergarten SET seat_county='Wrong county',seat_municipality_id=(SELECT id FROM municipality WHERE key='varazdin')")
        check = (Path(__file__).resolve().parents[1] / 'src/KIDSic/db/alembic/versions/0013_kindergarten_seat.sql').read_text().split('\n-- statement\n')[0]
        with self.assertRaisesRegex(asyncpg.RaiseError, 'Review county differences.*Wrong county'):
            async with self.c.transaction():
                await self.c.execute(check)
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten_seat'),1)

    async def test_removing_geography_clears_the_seat_foreign_key_and_coordinates(self):
        from KIDSic.dao.concrete.source_state import SourceStateWriter
        await self.repo.import_snapshot(self.snapshot([NATIONAL, {**NATIONAL, 'Naziv':'DV Drugi'}]))
        owners = [r['id'] for r in await self.c.fetch('SELECT id FROM kindergarten ORDER BY id')]
        source = await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed) VALUES ('geography','Geo','Test','https://example.invalid/geo',true) RETURNING id")
        state = SourceStateWriter(self.c,source,datetime.now(timezone.utc))
        record = await state.record('one',{},owner=owners[0])
        await state.record('two',{},owner=owners[1])
        await state.finish()
        await self.c.execute("UPDATE kindergarten_seat SET geography_source_record_id=$2,longitude=16.3,latitude=46.3,attributes=jsonb_build_object('address',address) WHERE kindergarten_id=$1",owners[0],record)
        next_state = SourceStateWriter(self.c,source,datetime.now(timezone.utc))
        await next_state.record('two',{},owner=owners[1])
        await next_state.finish()
        seat = await self.c.fetchrow('SELECT geography_source_record_id,longitude,latitude FROM kindergarten_seat WHERE kindergarten_id=$1',owners[0])
        self.assertEqual(tuple(seat),(None,None,None))
        self.assertFalse(await self.c.fetchval('SELECT EXISTS(SELECT 1 FROM source_record WHERE id=$1)',record))

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

    async def test_writer_translates_driver_errors_and_releases_the_connection(self):
        import asyncpg
        before = self.pool.get_size() - self.pool.get_idle_size()
        with self.assertRaises(PersistenceError) as error:
            async with AsyncpgSourceUnitOfWork(self.pool):
                raise asyncpg.PostgresError('synthetic database failure')
        self.assertIsInstance(error.exception.__cause__, asyncpg.PostgresError)
        self.assertEqual(self.pool.get_size() - self.pool.get_idle_size(), before)

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
