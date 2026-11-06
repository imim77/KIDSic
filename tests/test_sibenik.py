"""Šibenik tests cover open-source imports, city isolation and reviewed facilities."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from urllib.parse import urlparse

from pydantic import ValidationError

from KIDSic.config.routing import ROUTING_CITIES
from KIDSic.dao.concrete.asyncpg_location import AsyncpgLocationRepository
from KIDSic.dao.concrete.asyncpg_source import AsyncpgSourceRepository
from KIDSic.db.database import database_pool
from KIDSic.dto.commute import CommuteQuery
from KIDSic.dto.day_route import DayJourneyRequest
from KIDSic.dto.location import LocationFeature, LocationQuery
from KIDSic.dto.municipality import resolve_municipality, supported_city_key
from KIDSic.dto.source import PlannedSource, SourceDefinition, SourceSnapshot
from KIDSic.integrations.concrete.address import normalized_address
from KIDSic.services.concrete.day_route import DayRouteService
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records
from test_journey import journey
from test_sources import NATIONAL, source_client

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sibenik_import', ROOT / 'data-enrichment/import_sibenik.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Importer = module.SibenikLocationImporter
DATA = json.loads((ROOT / 'data-enrichment/sibenik-reviewed-locations.geojson').read_text())


def criteria(**changes):
    return dict(city='Šibenik', home={'lat': 43.735, 'lon': 15.895},
        work={'lat': 43.721, 'lon': 15.908}, departure='2026-11-09T07:00', mode='TRANSIT') | changes


class SibenikContractTests(unittest.TestCase):
    def test_aliases_and_brodarica_require_the_correct_county(self):
        for name in ('Šibenik', 'sibenik', 'Šibeniku', 'Šibenika'):
            self.assertEqual(supported_city_key(name), 'sibenik')
            self.assertEqual(LocationQuery(city=name).city, name)
        self.assertEqual(resolve_municipality('Brodarica', 'Šibensko-kninska županija'), 'sibenik')
        self.assertIsNone(resolve_municipality('Brodarica', 'Zadarska županija'))
        self.assertIsNone(resolve_municipality('Vodice', 'Šibensko-kninska županija'))
        rows = normalize_records([{**NATIONAL, 'Mjesto': 'Brodarica',
            'Zupanija': 'Šibensko-kninska županija'}], 'national')
        self.assertEqual((rows[0].municipality, rows[0].scope), ('sibenik', 'institution'))

    def test_city_bounds_and_pinned_calendar_do_not_accept_other_cities(self):
        self.assertEqual(CommuteQuery(**criteria()).city, 'Šibenik')
        for day in ('2026-09-07', '2027-06-07'):
            CommuteQuery(**criteria(departure=day + 'T07:00'))
        for changes in ({'departure': '2026-09-06T07:00'}, {'departure': '2027-06-08T07:00'},
                        {'city': 'Zagreb'}, {'city': 'Rijeka'},
                        {'home': {'lat': 45.81, 'lon': 15.98}},
                        {'home': {'lat': float('nan'), 'lon': 15.9}}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                CommuteQuery(**criteria(**changes))
        self.assertEqual(normalized_address('Šubićevo šetalište 2, 22000 Šibenik', 'Šibenik'),
                         normalized_address('Šubićevo šetalište 2', 'Šibenik'))
        self.assertIn('zagreb', normalized_address('Ilica 10 Zagreb', 'Šibenik'))

    def test_only_reviewed_addressed_osm_facilities_are_accepted(self):
        self.assertEqual(len(Importer.reviewed(DATA)), 3)
        for change in ('empty', 'license', 'duplicate', 'address', 'coordinates', 'amenity'):
            data = deepcopy(DATA)
            accepted = next(f for f in data['features'] if f['properties']['review_status'] == 'matched')
            if change == 'empty': data['features'] = []
            if change == 'license': data['license'] = 'unknown'
            if change == 'duplicate': data['features'].append(deepcopy(accepted))
            if change == 'address': accepted['properties']['osm_tags'].pop('addr:street')
            if change == 'coordinates': accepted['geometry']['coordinates'] = [15.98, 45.81]
            if change == 'amenity': accepted['properties']['osm_tags']['amenity'] = 'school'
            with self.subTest(change=change), self.assertRaises(ValueError):
                Importer.reviewed(data)


class SibenikRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_sibenik_ranking_uses_its_catalogue_and_source(self):
        query = DayJourneyRequest(**criteria())
        feature = LocationFeature(id='si', geometry={'coordinates': (15.908, 43.724)}, properties={
            'location_id': 'si', 'kindergarten_id': 'parent', 'name': 'Synthetic',
            'location_name': 'Synthetic Šibenik', 'address': 'Test 1', 'city': 'Šibenik',
            'provider_kind': 'unknown', 'district': None, 'location_role': 'facility', 'sources': []})
        seat = feature.model_copy(update={'id': 'seat', 'properties': feature.properties.model_copy(
            update={'location_role': 'seat'})})
        locations = SimpleNamespace(list_locations=AsyncMock(return_value=SimpleNamespace(
            features=[feature, seat], metadata=SimpleNamespace(total=2))))
        planner = SimpleNamespace(plan=AsyncMock(side_effect=lambda origin, destination, departure, mode:
            journey(departure, 5, 'BUS')))
        result = await DayRouteService(locations, planner).recommend(query)
        self.assertEqual(result['city'], 'Šibenik')
        self.assertEqual((result['searched'], result['excluded']), (1, 1))
        self.assertEqual(result['sources']['gtfs_sha256'], ROUTING_CITIES['Šibenik'].gtfs_sha256)
        self.assertEqual(result['sources']['license'], 'Otvorena dozvola RH')
        self.assertEqual(result['sources']['service_end'], '2027-06-07')
        self.assertEqual(result['results'][0]['elapsed_seconds'], 20 * 60)
        self.assertEqual(locations.list_locations.await_args.args[0].city, 'Šibenik')


@unittest.skipUnless(os.getenv('KIDSIC_TEST_DATABASE_URL'), 'Set KIDSIC_TEST_DATABASE_URL')
class SibenikImportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        dsn = os.environ['KIDSIC_TEST_DATABASE_URL']
        if not urlparse(dsn).path.removeprefix('/').startswith('kidsic_test_'):
            raise ValueError('Use a disposable kidsic_test_* database.')
        self.ctx = database_pool(dsn)
        self.pool = await self.ctx.__aenter__()
        self.c = await self.pool.acquire()
        self.tx = self.c.transaction()
        await self.tx.start()
        client = source_client()
        source = PlannedSource(SourceDefinition('national', 'https://data.gov.hr/ckan',
            'djecji-vrtici', 'national'), client.get_package.return_value,
            client.get_package.return_value.resources[0])
        records = [{**NATIONAL, 'Naziv': f['properties']['parent_name'],
                    'Mjesto': f['properties']['parent_settlement'],
                    'Zupanija': 'Grad Zagreb' if f['properties']['parent_settlement'] == 'Zagreb'
                        else 'Šibensko-kninska županija'} for f in Importer.reviewed(DATA)]
        await AsyncpgSourceRepository(self.c).import_snapshot(SourceSnapshot(source,
            normalize_records(records, 'national'), datetime.now(timezone.utc)))
        self.importer = Importer(self.c)

    async def asyncTearDown(self):
        await self.tx.rollback()
        await self.pool.release(self.c)
        await self.ctx.__aexit__(None, None, None)

    async def test_repeatable_import_preserves_seats_and_field_evidence(self):
        self.assertEqual(await self.importer.apply(DATA), {'imported': 3, 'excluded': 4})
        first = await self.c.fetch('SELECT id,kindergarten_id FROM location ORDER BY id')
        await self.importer.apply(DATA)
        self.assertEqual(first, await self.c.fetch('SELECT id,kindergarten_id FROM location ORDER BY id'))
        self.assertEqual(await self.c.fetchval('SELECT count(*) FROM kindergarten'), 3)
        self.assertEqual(await self.c.fetchval("SELECT seat_settlement FROM kindergarten WHERE name LIKE '%Hozana%'"), 'Zagreb')
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Šibenik'))
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row['location_role'], 'facility')
            self.assertEqual(row['field_sources']['longitude']['license'], 'ODbL-1.0')

    async def test_changed_parent_and_revocation_preserve_the_last_good_batch(self):
        await self.importer.apply(DATA)
        before = await self.c.fetchval("SELECT active_batch_id FROM data_source WHERE dataset_key=$1", module.SOURCE_KEY)
        changed = deepcopy(DATA)
        accepted = Importer.reviewed(changed)
        accepted[0]['properties']['parent_name'] = accepted[1]['properties']['parent_name']
        with self.assertRaises(ValueError):
            async with self.c.transaction():
                await self.importer.apply(changed)
        self.assertEqual(before, await self.c.fetchval("SELECT active_batch_id FROM data_source WHERE dataset_key=$1", module.SOURCE_KEY))
        await self.c.execute('UPDATE data_source SET import_allowed=false WHERE dataset_key=$1', module.SOURCE_KEY)
        with self.assertRaises(ValueError):
            async with self.c.transaction():
                await self.importer.apply(DATA)
        rows = await AsyncpgLocationRepository(self.c).list_locations(LocationQuery(city='Šibenik'))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['location_role'] == 'seat' for r in rows))
