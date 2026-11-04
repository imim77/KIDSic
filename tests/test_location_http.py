"""Location HTTP tests exercise real ASGI routing without requiring a database."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from KIDSic.exceptions import PersistenceError
from starlette.testclient import TestClient

from KIDSic.api.locations import create_app
from KIDSic.dto.location import LocationCollection


def empty_collection():
    return LocationCollection(features=[], metadata={
        'total': 0, 'mapped': 0, 'unmapped': 0, 'scope': 'city',
    })


class LocationHttpTests(unittest.TestCase):
    def test_geojson_response_and_query_filters(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        with TestClient(create_app(service)) as client:
            response = client.get('/api/locations', params={
                'city': ' Zagreb ', 'q': 'Medo', 'provider_kind': 'private',
                'bbox': '15,45,16,46', 'area': ' Banfica ',
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/geo+json')
        self.assertEqual(response.json()['metadata']['total'], 0)
        query = service.list_locations.await_args.args[0]
        self.assertEqual((query.city, query.q, query.provider_kind), ('Zagreb', 'Medo', 'private'))
        self.assertEqual(query.area, 'Banfica')
        self.assertEqual(query.bbox, (15, 45, 16, 46))

    def test_invalid_queries_never_access_persistence(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        with TestClient(create_app(service)) as client:
            for suffix in ('city=Split', 'city=Osijek', 'city=', 'provider_kind=city', 'bbox=bad', 'bbox=nan,45,16,46',
                           'city=Zagreb&city=Split', 'limit=1', 'q=' + 'a' * 201, 'area=' + 'a' * 201, 'area=Banfica&area=Centar'):
                with self.subTest(suffix=suffix):
                    response = client.get('/api/locations?' + suffix)
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(response.json(), {'error': 'invalid_query'})
            self.assertEqual(client.post('/api/locations').status_code, 405)
        service.list_locations.assert_not_awaited()

    def test_database_failures_return_sanitized_service_unavailable(self):
        for error in (OSError('secret DSN'), TimeoutError('secret DSN'),
                      PersistenceError('secret SQL'), PersistenceError('pool closed')):
            service = SimpleNamespace(list_locations=AsyncMock(side_effect=error))
            with self.subTest(error=type(error)), TestClient(create_app(service)) as client:
                with self.assertLogs('KIDSic.api.locations', level='ERROR'):
                    response = client.get('/api/locations')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {'error': 'locations_unavailable'})

    def test_default_app_owns_service_lifespan_once(self):
        events = []
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        @asynccontextmanager
        async def locations():
            events.append('open')
            yield service
            events.append('close')
        with patch('KIDSic.api.locations.Settings.from_env'), \
             patch('KIDSic.api.locations.DependencyService') as dependencies:
            dependencies.return_value.location_service = locations
            app = create_app()
            with TestClient(app) as client:
                self.assertEqual(client.get('/api/locations').status_code, 200)
                self.assertEqual(client.get('/api/locations').status_code, 200)
                self.assertEqual(events, ['open'])
            self.assertEqual(events, ['open', 'close'])
            self.assertFalse(hasattr(app.state, 'locations'))
