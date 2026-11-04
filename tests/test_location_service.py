"""LocationService keeps unidentified coordinates visible without fabricating points."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from KIDSic.dto.location import LocationQuery
from KIDSic.factories.location import LocationServiceFactory


class LocationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_geocoded_seat_keeps_seat_identity_and_maps_with_evidence(self):
        institution = uuid4()
        source = {'name':'Geo','url':'https://example.invalid','reference_date':None,
                  'retrieved_at':datetime(2026,11,3,tzinfo=timezone.utc),'active_snapshot':True}
        row = dict(kindergarten_id=institution,name='Seat',location_name='Seat',location_id=None,
                   address='Seat 1',city='Varaždin',provider_kind='childminder',district=None,
                   longitude=16.3,latitude=46.3,location_role='seat',sources=[source],
                   field_sources={'longitude':source,'latitude':source})
        @asynccontextmanager
        async def uow():
            yield SimpleNamespace(locations=SimpleNamespace(list_locations=AsyncMock(return_value=[row])))
        result = await LocationServiceFactory().create(uow).list_locations(LocationQuery(city='Varaždin'))
        self.assertEqual(result.metadata.mapped,1)
        self.assertEqual(result.features[0].id,f'seat:{institution}')
        self.assertEqual(result.features[0].properties.location_role,'seat')
        self.assertEqual(result.features[0].geometry.coordinates,(16.3,46.3))

    async def test_snapshot_counts_identity_sources_and_null_geometry(self):
        institution = uuid4()
        location = uuid4()
        source = {'name': 'Synthetic', 'url': 'https://example.invalid',
                  'reference_date': None, 'retrieved_at': datetime(2026, 11, 2, tzinfo=timezone.utc)}
        row = dict(kindergarten_id=institution, name='Synthetic', location_name='Branch',
                   address=None, city='Zagreb', provider_kind='unknown', district=None,
                   website_url='https://example.invalid/kindergarten',email='info@example.invalid',phone='01/123-4567',
                   longitude=15.98, latitude=45.81, sources=[source])
        repository = SimpleNamespace(list_locations=AsyncMock(return_value=[
            dict(row, location_id=location, location_role='facility', field_sources={
                'longitude': dict(source, active_snapshot=False),
            }),
            dict(row, location_id=uuid4(), location_role='facility', longitude=None, latitude=None),
            dict(row, location_id=None, location_role='seat'),
        ]))
        events = []
        @asynccontextmanager
        async def uow():
            events.append('enter')
            yield SimpleNamespace(locations=repository)
            events.append('exit')
        query = LocationQuery()
        result = await LocationServiceFactory().create(uow).list_locations(query)
        repository.list_locations.assert_awaited_once_with(query)
        self.assertEqual(events, ['enter', 'exit'])
        self.assertEqual(result.metadata.model_dump(), {
            'total': 3, 'mapped': 1, 'unmapped': 2, 'scope': 'city', 'complete': True, 'confirmed': 0, 'unknown': 0,
        })
        payload = result.model_dump(mode='json')
        self.assertEqual(payload['features'][0]['id'], str(location))
        self.assertEqual(payload['features'][0]['geometry']['coordinates'], [15.98, 45.81])
        self.assertEqual(payload['features'][0]['properties']['sources'][0]['retrieved_at'],
                         '2026-11-02T00:00:00Z')
        evidence = payload['features'][0]['properties']['field_sources']['longitude']
        self.assertFalse(evidence['active_snapshot'])
        self.assertEqual(evidence['retrieved_at'], '2026-11-02T00:00:00Z')
        self.assertEqual(payload['features'][1]['properties']['field_sources'], {})
        self.assertIsNone(payload['features'][1]['geometry'])
        self.assertEqual(payload['features'][2]['id'], f'seat:{institution}')
        self.assertIsNone(payload['features'][2]['geometry'])
        self.assertIsNone(payload['features'][0]['properties']['age_groups'])
        self.assertEqual(payload['features'][0]['properties']['website_url'], 'https://example.invalid/kindergarten')
        self.assertEqual(payload['features'][0]['properties']['email'], 'info@example.invalid')
        self.assertEqual(payload['features'][0]['properties']['phone'], '01/123-4567')

    async def test_suitability_counts_and_sourced_programs_survive_geojson_conversion(self):
        row = dict(kindergarten_id=uuid4(),name='Synthetic',location_name='Synthetic',location_id=uuid4(),
            address=None,city='Zagreb',provider_kind='private',district=None,longitude=None,latitude=None,
            location_role='facility',sources=[],suitability_status='confirmed',programs=[{
                'program_id':str(uuid4()),'name':'Montessori','min_age_months':12,'max_age_months_exclusive':36,
                'verified_on':'2026-11-04','valid_until':None,'source_record_id':str(uuid4()),
                'source_url':'https://example.invalid/program','source_title':'Synthetic source','scope':'facility',
            }])
        @asynccontextmanager
        async def uow():
            yield SimpleNamespace(locations=SimpleNamespace(list_locations=AsyncMock(return_value=[
                row,dict(row,location_id=uuid4(),suitability_status='unknown',programs=[])])))
        result = await LocationServiceFactory().create(uow).list_locations(LocationQuery(age_months=24))
        self.assertEqual((result.metadata.total,result.metadata.confirmed,result.metadata.unknown),(2,1,1))
        self.assertEqual(result.features[0].properties.programs[0].source_url,'https://example.invalid/program')
