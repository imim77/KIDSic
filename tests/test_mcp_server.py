"""MCP tests exercise protocol negotiation, discovery, reads and calls over HTTP."""
from contextlib import asynccontextmanager
import base64
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from KIDSic.dto.location import LocationCollection
from KIDSic.api.mcp_server import create_app, UI_URI, UI_MIME


def empty_collection():
    return LocationCollection(features=[], metadata={
        'total': 0, 'mapped': 0, 'unmapped': 0, 'scope': 'city',
    })


def decoded_locations(result):
    payload = result.meta['locations']
    return json.loads(gzip.decompress(base64.b64decode(payload['data'])))


@asynccontextmanager
async def connected(service):
    with TemporaryDirectory() as directory:
        asset = Path(directory) / 'mcp.html'
        asset.write_text('<html><body>KIDSic map</body></html>')
        app = create_app(service, ui_path=asset)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),
                                         base_url='http://localhost') as http:
                async with streamable_http_client('http://localhost/mcp',
                                                   http_client=http) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        initialized = await session.initialize()
                        yield session, initialized


class McpServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_links_required_city_tool_to_html_resource(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, initialized):
            self.assertIn('ALWAYS', initialized.instructions)
            self.assertIn('ask the user', initialized.instructions)
            tools = (await session.list_tools()).tools
            self.assertEqual([tool.name for tool in tools], ['prikazi_vrtice'])
            tool = tools[0]
            self.assertEqual(tool.inputSchema['required'], ['city'])
            self.assertNotIn('default', tool.inputSchema['properties']['city'])
            self.assertEqual(set(tool.inputSchema['properties']), {'city', 'name', 'provider_kind'})
            self.assertEqual(set(tool.inputSchema['properties']['provider_kind']['anyOf'][0]['enum']),
                             {'municipal', 'private', 'religious', 'childminder', 'other', 'unknown'})
            self.assertEqual(tool.inputSchema['properties']['name']['maxLength'], 200)
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertEqual(tool.meta['ui']['resourceUri'], UI_URI)
            self.assertEqual(tool.meta['openai/outputTemplate'], UI_URI)
            resources = (await session.list_resources()).resources
            self.assertEqual(str(resources[0].uri), UI_URI)
            resource = (await session.read_resource(UI_URI)).contents[0]
            self.assertEqual(resource.mimeType, UI_MIME)
            self.assertIn('KIDSic map', resource.text)
            self.assertIn('https://api.mapbox.com',
                          resource.meta['ui']['csp']['connectDomains'])
            self.assertIn('blob:', resource.meta['ui']['csp']['resourceDomains'])
        service.list_locations.assert_not_awaited()

    async def test_city_is_trimmed_and_empty_results_still_have_map_contract(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        async with connected(service) as (session, _):
            result = await session.call_tool('prikazi_vrtice', {'city': ' Rijeka '})
            self.assertFalse(result.isError)
            self.assertEqual(result.structuredContent['city'], 'Rijeka')
            self.assertEqual(decoded_locations(result)['features'], [])
            self.assertEqual(result.meta['ui']['resourceUri'], UI_URI)
            self.assertEqual(result.structuredContent['metadata']['total'], 0)
            self.assertNotIn('locations', result.structuredContent)
        query = service.list_locations.await_args.args[0]
        self.assertEqual(query.city, 'Rijeka')
        self.assertEqual(query.q, '')

    async def test_missing_blank_invalid_city_never_reads_database(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, _):
            for arguments in ({}, {'city': ''}, {'city': '   '}, {'city': None},
                              {'city': 123}, {'city': 'a' * 101}, {'city': 'Split'}, {'city': 'Osijek'},
                              {'city': 'Zagreb', 'unexpected': 'value'}):
                with self.subTest(arguments=arguments):
                    result = await session.call_tool('prikazi_vrtice', arguments)
                    self.assertTrue(result.isError)
                    self.assertIsNone(result.structuredContent)
                    self.assertIn('grad', result.content[0].text.lower())
        service.list_locations.assert_not_awaited()

    async def test_map_payload_is_complete_but_kept_out_of_model_summary(self):
        payload = LocationCollection(features=[{
            'id': 'test-seat', 'geometry': None, 'properties': {
                'location_id': None, 'kindergarten_id': 'test-kindergarten',
                'name': 'Synthetic test institution', 'location_name': 'Synthetic seat',
                'address': None, 'city': 'Rijeka', 'provider_kind': 'unknown',
                'district': None, 'location_role': 'seat', 'sources': [],
            },
        }], metadata={'total': 1, 'mapped': 0, 'unmapped': 1, 'scope': 'city'})
        service = SimpleNamespace(list_locations=AsyncMock(return_value=payload))
        async with connected(service) as (session, _):
            result = await session.call_tool('prikazi_vrtice', {'city': 'Rijeka'})
            self.assertFalse(result.isError)
            self.assertEqual(result.meta['locations']['encoding'], 'gzip+base64')
            self.assertEqual(decoded_locations(result), payload.model_dump(mode='json'))
            self.assertEqual(result.structuredContent, {
                'city': 'Rijeka', 'name': '', 'provider_kind': None, 'metadata': payload.metadata.model_dump(mode='json'),
            })
            self.assertNotIn('Synthetic', str(result.structuredContent))

    async def test_city_and_name_search_preserves_criteria_and_handles_zero_matches(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        cases = [(' Zagrebu ', ' Bajka ', 'Zagreb', 'Bajka'),
                 ('varaždinu', 'Čarobna kućica', 'Varaždin', 'Čarobna kućica'),
                 ('Rijeci', 'Zamet', 'Rijeka', 'Zamet'),
                 ('Rijeka', '', 'Rijeka', ''), ('Zagreb', '   ', 'Zagreb', ''),
                 ('Zagreb', '100%_Medo', 'Zagreb', '100%_Medo')]
        async with connected(service) as (session, _):
            for city, name, expected_city, expected_name in cases:
                with self.subTest(city=city, name=name):
                    service.list_locations.reset_mock()
                    result = await session.call_tool('prikazi_vrtice', {'city': city, 'name': name})
                    self.assertFalse(result.isError)
                    self.assertEqual(result.structuredContent['city'], expected_city)
                    self.assertEqual(result.structuredContent['name'], expected_name)
                    self.assertEqual(decoded_locations(result)['features'], [])
                    service.list_locations.assert_awaited_once()
                    query = service.list_locations.await_args.args[0]
                    self.assertEqual((query.city, query.q), (expected_city, expected_name))
                    if expected_name:
                        self.assertIn('skrati naziv', result.content[0].text)

    async def test_name_does_not_supply_a_missing_city_and_invalid_names_never_read(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, _):
            missing = await session.call_tool('prikazi_vrtice', {'name': 'Bajka'})
            self.assertTrue(missing.isError)
            self.assertIn('U kojem gradu', missing.content[0].text)
            for name in (None, 123, [], {}, 'x' * 201):
                with self.subTest(name=name):
                    result = await session.call_tool('prikazi_vrtice', {'city': 'Zagreb', 'name': name})
                    self.assertTrue(result.isError)
                    self.assertIn('Naziv', result.content[0].text)
        service.list_locations.assert_not_awaited()

    async def test_provider_type_combines_with_city_and_name_without_broadening_empty_results(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        async with connected(service) as (session, _):
            for kind in ('municipal', 'private', 'religious', 'childminder', 'other', 'unknown', None):
                with self.subTest(kind=kind):
                    service.list_locations.reset_mock()
                    result = await session.call_tool('prikazi_vrtice', {
                        'city': 'Zagrebu', 'name': ' Bajka ', 'provider_kind': kind})
                    self.assertFalse(result.isError)
                    self.assertEqual(result.structuredContent['provider_kind'], kind)
                    query = service.list_locations.await_args.args[0]
                    self.assertEqual((query.city, query.q, query.provider_kind), ('Zagreb', 'Bajka', kind))
                    service.list_locations.assert_awaited_once()
                    self.assertEqual(decoded_locations(result)['features'], [])
                    self.assertIn('Nemoj', result.content[0].text)

    async def test_invalid_or_multiple_types_and_missing_city_never_read_database(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, _):
            missing = await session.call_tool('prikazi_vrtice', {'provider_kind': 'municipal'})
            self.assertTrue(missing.isError)
            self.assertIn('U kojem gradu', missing.content[0].text)
            for kind in ('', 'gradski', 'MUNICIPAL', 'private,religious', ['private', 'religious'], {}, 1, True):
                with self.subTest(kind=kind):
                    result = await session.call_tool('prikazi_vrtice', {'city': 'Rijeka', 'provider_kind': kind})
                    self.assertTrue(result.isError)
                    self.assertIn('Vrsta (provider_kind)', result.content[0].text)
        service.list_locations.assert_not_awaited()

    async def test_service_errors_are_sanitized_without_false_empty_map(self):
        service = SimpleNamespace(list_locations=AsyncMock(side_effect=RuntimeError('secret DSN')))
        async with connected(service) as (session, _):
            with self.assertLogs('KIDSic.api.location_tools', level='ERROR'):
                result = await session.call_tool('prikazi_vrtice', {'city': 'Zagreb'})
            self.assertTrue(result.isError)
            self.assertIsNone(result.structuredContent)
            self.assertNotIn('secret', result.model_dump_json())

    async def test_large_city_fits_host_budget_without_losing_provenance(self):
        features = []
        for index in range(461):
            source = {
                'name': 'Synthetic city directory',
                'url': 'https://example.invalid/source',
                'reference_date': None, 'retrieved_at': '2026-11-03T10:00:00Z',
            }
            features.append({
                'id': f'location-{index}',
                'geometry': {'coordinates': [15.9 + index / 10000, 45.8]},
                'properties': {
                    'location_id': f'location-{index}',
                    'kindergarten_id': f'kindergarten-{index}',
                    'name': f'Synthetic institution {index}',
                    'location_name': f'Synthetic facility Čarobna kućica {index}',
                    'address': f'Synthetic address {index}', 'city': 'Zagreb',
                    'provider_kind': 'municipal', 'district': None,
                    'location_role': 'facility', 'sources': [source],
                    'field_sources': {key: {**source, 'active_snapshot': True}
                                      for key in ('name', 'address', 'longitude', 'latitude')},
                },
            })
        payload = LocationCollection(features=features, metadata={
            'total': 461, 'mapped': 461, 'unmapped': 0, 'scope': 'city',
        })
        self.assertGreater(len(payload.model_dump_json().encode()), 500_000)
        service = SimpleNamespace(list_locations=AsyncMock(return_value=payload))
        async with connected(service) as (session, _):
            result = await session.call_tool('prikazi_vrtice', {'city': 'Zagreb'})
            self.assertLess(len(result.model_dump_json().encode()), 130_000)
            self.assertEqual(decoded_locations(result), payload.model_dump(mode='json'))

    async def test_unbuilt_ui_prevents_startup_before_opening_database(self):
        app = create_app(ui_path='/nonexistent/kidsic/mcp.html')
        with patch('KIDSic.api.mcp_server.DependencyService') as dependencies:
            with self.assertRaisesRegex(RuntimeError, 'build:mcp'):
                async with app.router.lifespan_context(app):
                    self.fail('Startup should fail before accepting requests.')
            dependencies.assert_not_called()

    async def test_default_app_owns_one_service_for_multiple_tool_calls(self):
        events = []
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))

        @asynccontextmanager
        async def locations():
            events.append('open')
            yield service
            events.append('close')

        with TemporaryDirectory() as directory:
            asset = Path(directory) / 'mcp.html'
            asset.write_text('<html>map</html>')
            with patch('KIDSic.api.mcp_server.Settings.from_env'), \
                 patch('KIDSic.api.mcp_server.DependencyService') as dependencies:
                dependencies.return_value.location_service = locations
                app = create_app(ui_path=asset)
                async with app.router.lifespan_context(app):
                    self.assertEqual(events, ['open'])
                self.assertEqual(events, ['open', 'close'])
