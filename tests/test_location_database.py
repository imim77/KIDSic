"""Rollback-only location integration fixtures are synthetic, never real institutions."""
import os
from datetime import datetime, timezone
import unittest
from urllib.parse import urlparse
from uuid import uuid4

from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.db.database import database_pool
from KIDSic.dto.location import LocationQuery
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records


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

    async def test_contacts_prefer_the_active_facility_then_reviewed_phone_and_institution(self):
        owner, location = await self.fixture('Contact owner')
        await self.c.execute('''UPDATE kindergarten SET website_url='https://example.invalid/owner',
            email='owner@example.invalid',phone='01/111-1111' WHERE id=$1''', owner)
        await self.c.execute('UPDATE source_record SET raw_data=$2 WHERE location_id=$1', location, {
            'Web': ' https://example.invalid/branch ', 'Email': ' branch@example.invalid ',
            'Telefon': ' 01/222-2222 ',
        })
        branch = await self.c.fetchval('''INSERT INTO location
            (kindergarten_id,name,settlement,settlement_key,attributes)
            VALUES ($1,'Second branch','Zagreb','zagreb',$2) RETURNING id''',
            owner, {'phone': '01/333-3333'})
        await self.record(owner, branch)
        rows = {r['location_id']: r for r in await self.repository.list_locations(LocationQuery())}
        self.assertEqual(tuple(rows[location][key] for key in ('website_url','email','phone')),
                         ('https://example.invalid/branch','branch@example.invalid','01/222-2222'))
        self.assertEqual(tuple(rows[branch][key] for key in ('website_url','email','phone')),
                         ('https://example.invalid/owner','owner@example.invalid','01/333-3333'))
        # An older published contact does not override the currently available fallback.
        await self.c.execute('UPDATE source_record SET batch_id=$2 WHERE location_id=$1', location, uuid4())
        await self.record(owner, location)
        rows = {r['location_id']: r for r in await self.repository.list_locations(LocationQuery())}
        self.assertEqual(rows[location]['email'], 'owner@example.invalid')
        seat, _ = await self.fixture('Seat contact', seat=True)
        await self.c.execute("UPDATE kindergarten SET email='seat@example.invalid',phone=' ' WHERE id=$1", seat)
        rows = await self.repository.list_locations(LocationQuery(q='Seat contact'))
        self.assertEqual(rows[0]['email'], 'seat@example.invalid')
        self.assertIsNone(rows[0]['phone'])
        self.assertIsNone(rows[0]['website_url'])

    async def test_seat_geography_requires_current_address_and_approved_evidence(self):
        from KIDSic.dao.concrete.asyncpg_kindergarten import AsyncpgKindergartenRepository
        owner, _ = await self.fixture('Childminder seat', provider='childminder', seat=True)
        geo_source = await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ($1,'Geo','Test','https://example.invalid/geo',true,$2) RETURNING id", str(uuid4()), self.batch)
        record = await self.c.fetchval("INSERT INTO source_record(source_id,batch_id,raw_data,kindergarten_id,match_status,match_method) VALUES ($1,$2,'{}',$3,'accepted','manual') RETURNING id", geo_source, self.batch, owner)
        await self.c.execute("UPDATE kindergarten SET seat_longitude=15.98,seat_latitude=45.81,seat_attributes=$2,provenance=$3 WHERE id=$1", owner,
                             {'address':'Seat 1','quarter':'Synthetic quarter','suburb':'Banfica','neighbourhood':'Synthetic neighbourhood','settlement':'Zagreb'},
                             {'seat_geography':{'source_record_id':str(record)}})
        await self.c.execute('UPDATE source_record SET raw_data=$2 WHERE id=$1', record,
                             {'evidence_scope':'registered_seat_geography'})
        await self.c.execute("INSERT INTO knowledge_chunk(kindergarten_id,source_record_id,ordinal,content,source_url,content_sha256) VALUES ($1,$2,0,'Banfica seat geography','https://example.invalid/geo',$3)", owner, record, 'a'*64)
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual((rows[0]['location_id'],rows[0]['location_role'],rows[0]['longitude']), (None,'seat',15.98))
        self.assertIn('longitude', rows[0]['field_sources'])
        self.assertIn('Banfica', rows[0]['areas'])
        self.assertEqual(len(await self.repository.list_locations(LocationQuery(area='banfica'))), 1)
        search = AsyncpgKindergartenRepository(self.c)
        self.assertIn('Banfica', [r['name'] for r in await search.list_areas(city='Zagreb')])
        from KIDSic.services.concrete.request_parser import parse_request
        self.assertNotIn('area', await parse_request(search, 'Dijete od 2 godine Zagreb'))
        self.assertEqual((await parse_request(search, 'Dijete od 2 godine Zagreb na Banfici'))['area'], 'Banfica')
        options = await search.find_options(city='Zagreb',age_months=24,area='Banfica',include_unknown=True)
        self.assertEqual([r['kindergarten_id'] for r in options], [owner])
        self.assertEqual(options[0]['neighbourhood'], 'Synthetic neighbourhood')
        self.assertEqual(len(await search.retrieve_context(location_ids=[],kindergarten_ids=[owner],text='Banfica')), 1)
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE id=$1', geo_source)
        self.assertIsNone((await self.repository.list_locations(LocationQuery()))[0]['longitude'])
        self.assertEqual(await self.repository.list_locations(LocationQuery(area='Banfica')), [])
        self.assertEqual(await search.list_areas(city='Zagreb'), [])
        await self.c.execute('UPDATE data_source SET import_allowed=true WHERE id=$1', geo_source)
        await self.c.execute("UPDATE kindergarten SET seat_address='New seat 2' WHERE id=$1", owner)
        self.assertEqual(await self.repository.list_locations(LocationQuery(area='Banfica')), [])
        self.assertIsNone((await self.repository.list_locations(LocationQuery()))[0]['longitude'])
        self.assertEqual(await search.find_options(city='Zagreb',age_months=24,area='Banfica',include_unknown=True), [])
        self.assertEqual(await search.retrieve_context(location_ids=[],kindergarten_ids=[owner],text='Banfica'), [])
        self.assertEqual(await self.repository.list_locations(LocationQuery(bbox=(15,45,16,46))), [])
        # Evidence linked to another institution never authorizes a pin.
        await self.c.execute("UPDATE kindergarten SET seat_address='Seat 1',provenance=$2 WHERE id=$1", owner,
                             {'seat_geography':{'source_record_id':str(uuid4())}})
        self.assertIsNone((await self.repository.list_locations(LocationQuery()))[0]['longitude'])

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
        with self.assertRaises(ValueError):
            LocationQuery(city='Split')

    async def test_complete_city_has_no_recommendation_limit(self):
        for i in range(101):
            await self.fixture(f'Facility {i}')
        self.assertEqual(len(await self.repository.list_locations(LocationQuery())), 101)

    async def test_all_provider_types_filter_exactly_with_city_name_and_unmapped_locations(self):
        kinds = ('municipal', 'private', 'religious', 'childminder', 'other', 'unknown')
        expected = {}
        for kind in kinds:
            _, expected[kind] = await self.fixture('Bajka ' + kind, provider=kind,
                coords=(None, None) if kind in ('childminder', 'unknown') else (15.98, 45.81))
        await self.fixture('Bajka outside city', city='Rijeka', provider='private')
        await self.fixture('Other name', provider='private')
        for kind in kinds:
            rows = await self.repository.list_locations(LocationQuery(city='Zagreb', q='Bajka', provider_kind=kind))
            self.assertEqual([r['location_id'] for r in rows], [expected[kind]])
            self.assertEqual({r['provider_kind'] for r in rows}, {kind})
            self.assertEqual(await self.repository.list_locations(
                LocationQuery(city='Zagreb', q='No matching name', provider_kind=kind)), [])
        rows = await self.repository.list_locations(LocationQuery(city='Zagreb', q='Bajka'))
        self.assertEqual({r['location_id'] for r in rows}, set(expected.values()))

    async def test_area_filters_attested_fields_exactly_and_combines_with_other_filters(self):
        expected = []
        for field in ('district', 'quarter', 'suburb', 'neighbourhood', 'settlement'):
            _, location = await self.fixture('Bajka ' + field, provider='private', coords=(None, None))
            if field == 'district':
                await self.c.execute("UPDATE location SET district='Črnomerec' WHERE id=$1", location)
            elif field == 'settlement':
                await self.c.execute("UPDATE location SET settlement='Črnomerec',settlement_key='crnomerec',municipality_id=$2 WHERE id=$1", location, self.municipality)
            else:
                await self.c.execute('UPDATE location SET attributes=$2 WHERE id=$1', location, {field:'Črnomerec'})
            expected.append(location)
        _, wrong_type = await self.fixture('Bajka municipal')
        await self.c.execute("UPDATE location SET district='Črnomerec' WHERE id=$1", wrong_type)
        await self.fixture('Črnomerec name only', provider='private')
        _, address_only = await self.fixture('Bajka address', provider='private')
        await self.c.execute("UPDATE location SET address='Črnomerec 1' WHERE id=$1", address_only)
        _, wrong_city = await self.fixture('Bajka Rijeka', city='Rijeka', provider='private')
        await self.c.execute("UPDATE location SET district='Črnomerec' WHERE id=$1", wrong_city)
        for area in ('Črnomerec', ' CRNOMEREC '):
            rows = await self.repository.list_locations(LocationQuery(city='Zagreb',q='Bajka',provider_kind='private',area=area))
            self.assertEqual({r['location_id'] for r in rows}, set(expected))
            self.assertTrue(all('Črnomerec' in r['areas'] and r['longitude'] is None for r in rows))
        for area in ('Črno', '%', "' OR 1=1 --", 'Missing area'):
            self.assertEqual(await self.repository.list_locations(LocationQuery(area=area)), [])
        self.assertEqual(len(await self.repository.list_locations(LocationQuery(area='   '))), 8)
        self.assertEqual(await self.repository.list_locations(LocationQuery(city='Zagrebu',area='Zagreb')), [])
        await self.c.execute("UPDATE location SET attributes=$2 WHERE id=$1", expected[1], {'quarter':'Mjesni odbor Zamet'})
        for area in ('Zamet','mjesni odbor ZAMET'):
            self.assertEqual([r['location_id'] for r in await self.repository.list_locations(LocationQuery(area=area))], [expected[1]])

    async def test_area_evidence_must_be_current_allowed_and_belong_to_exact_object(self):
        owner, location = await self.fixture('Target')
        record = await self.c.fetchval('SELECT id FROM source_record WHERE location_id=$1', location)
        other, other_location = await self.fixture('Other')
        other_record = await self.c.fetchval('SELECT id FROM source_record WHERE location_id=$1', other_location)
        sibling = await self.c.fetchval("INSERT INTO location(kindergarten_id,name,settlement,settlement_key) VALUES ($1,'Sibling','Zagreb','zagreb') RETURNING id", owner)
        await self.record(owner, sibling)
        sibling_record = await self.c.fetchval('SELECT id FROM source_record WHERE location_id=$1', sibling)
        alternate = await self.c.fetchval("INSERT INTO data_source(dataset_key,title,publisher,url,import_allowed,active_batch_id) VALUES ($1,'Current','Test','https://example.invalid/current',true,$2) RETURNING id", str(uuid4()), self.batch)
        await self.record(owner, location, source=alternate)
        await self.c.execute("UPDATE location SET district='Banfica',attributes=$2 WHERE id=$1", location, {'quarter':'Banfica','suburb':'Banfica','neighbourhood':'Banfica'})
        for pointer, status, allowed, batch in (
            (record, 'accepted', True, self.batch),
            (record, 'rejected', True, self.batch),
            (record, 'candidate', True, self.batch),
            (record, 'accepted', False, self.batch),
            (record, 'accepted', True, uuid4()),
            (other_record, 'accepted', True, self.batch),
            (sibling_record, 'accepted', True, self.batch),
            (uuid4(), 'accepted', True, self.batch),
        ):
            await self.c.execute('UPDATE source_record SET match_status=$2,batch_id=$3 WHERE id=$1', record, status, batch)
            await self.c.execute('UPDATE data_source SET import_allowed=$2 WHERE id=$1', self.source, allowed)
            await self.c.execute('UPDATE location SET provenance=$2 WHERE id=$1', location,
                {key:{'source_record_id':str(pointer)} for key in ('district','quarter','suburb','neighbourhood')})
            rows = await self.repository.list_locations(LocationQuery(q='Target', area='Banfica'))
            valid = pointer == record and status == 'accepted' and allowed and batch == self.batch
            self.assertEqual([r['location_id'] for r in rows], [location] if valid else [])
            unfiltered = await self.repository.list_locations(LocationQuery(q='Target'))
            self.assertIn(location, [r['location_id'] for r in unfiltered])

    async def test_name_search_matches_parent_and_branch_with_croatian_letters_and_city_scope(self):
        _, branch = await self.fixture('Dječji vrtić Čarobna kućica')
        await self.c.execute("UPDATE location SET name='Đački kutak' WHERE id=$1", branch)
        await self.fixture('Dječji vrtić Čarobna kućica', city='Rijeka')
        await self.fixture('Other')
        for query in ('ČAROBNA', 'carobna', 'kućica', 'KUCICA', 'Đački', 'dacki'):
            with self.subTest(query=query):
                rows = await self.repository.list_locations(LocationQuery(city='Zagreb', q=query))
                self.assertEqual([r['location_id'] for r in rows], [branch])
        self.assertEqual(await self.repository.list_locations(LocationQuery(q="%' OR 1=1 --")), [])

    async def test_reimport_exposes_last_known_coordinate_evidence_without_relabeling_it(self):
        from test_sources import MUNICIPAL, source_client
        client = source_client('municipal')
        package = client.get_package.return_value
        source = PlannedSource(SourceDefinition('coordinate-history', 'https://data.zagreb.hr',
            'gradski_vrtici_grada_zagreba', 'municipal'), package, package.resources[0])
        importer = AsyncpgSourceRepository(self.c)
        earlier = datetime(2026, 10, 1, tzinfo=timezone.utc)
        current = datetime(2026, 11, 1, tzinfo=timezone.utc)
        await importer.import_snapshot(SourceSnapshot(source,
            normalize_records([MUNICIPAL], 'municipal'), earlier))
        await importer.import_snapshot(SourceSnapshot(source, normalize_records([
            {**MUNICIPAL, 'X': None, 'Y': None, 'GradskaCetvrt': None}], 'municipal'), current))
        rows = await self.repository.list_locations(LocationQuery())
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['longitude'], rows[0]['latitude']), (15.9452, 45.8017))
        fields = rows[0]['field_sources']
        self.assertFalse(fields['longitude']['active_snapshot'])
        self.assertFalse(fields['latitude']['active_snapshot'])
        self.assertFalse(fields['district']['active_snapshot'])
        self.assertEqual(datetime.fromisoformat(fields['longitude']['retrieved_at']), earlier)
        self.assertIsNone(fields['longitude']['reference_date'])
        self.assertTrue(fields['address']['active_snapshot'])
        self.assertEqual(datetime.fromisoformat(fields['address']['retrieved_at']), current)
        self.assertEqual(datetime.fromisoformat(rows[0]['sources'][0]['retrieved_at']), current)

    async def test_invalid_coordinate_provenance_keeps_list_entry_but_excludes_point_and_bbox(self):
        owner, location = await self.fixture('Target')
        evidence = await self.c.fetchval('SELECT id FROM source_record WHERE location_id=$1', location)
        alternate = await self.c.fetchval('''INSERT INTO data_source
            (dataset_key,title,publisher,url,import_allowed,active_batch_id)
            VALUES ($1,'Current','Test','https://example.invalid/current',true,$2)
            RETURNING id''', str(uuid4()), self.batch)
        await self.record(owner, location, source=alternate)
        _, other_location = await self.fixture('Other')
        wrong_owner = await self.c.fetchval('SELECT id FROM source_record WHERE location_id=$1', other_location)
        same_owner_location = await self.c.fetchval('''INSERT INTO location
            (kindergarten_id,name,settlement,settlement_key)
            VALUES ($1,'Other branch','Zagreb','zagreb') RETURNING id''', owner)
        await self.record(owner, same_owner_location, active=False)
        wrong_location = await self.c.fetchval('SELECT id FROM source_record WHERE location_id=$1',
                                              same_owner_location)
        for label, pointer, status, allowed in (
            ('rejected', evidence, 'rejected', True),
            ('candidate', evidence, 'candidate', True),
            ('wrong_owner', wrong_owner, 'accepted', True),
            ('wrong_location', wrong_location, 'accepted', True),
            ('disabled', evidence, 'accepted', False),
        ):
            with self.subTest(label=label):
                await self.c.execute('UPDATE source_record SET match_status=$2 WHERE id=$1', evidence, status)
                await self.c.execute('UPDATE data_source SET import_allowed=$2 WHERE id=$1', self.source, allowed)
                await self.c.execute('UPDATE location SET provenance=$2 WHERE id=$1', location, {
                    key: {'source_record_id': str(pointer)} for key in ('longitude', 'latitude')})
                rows = await self.repository.list_locations(LocationQuery(q='Target'))
                self.assertEqual(len(rows), 1)
                self.assertIsNone(rows[0]['longitude'])
                self.assertIsNone(rows[0]['latitude'])
                self.assertNotIn('longitude', rows[0]['field_sources'])
                self.assertEqual(await self.repository.list_locations(
                    LocationQuery(q='Target', bbox=(15, 45, 16, 46))), [])
