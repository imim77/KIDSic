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
async def connected(service, rag_service=None):
    with TemporaryDirectory() as directory:
        asset = Path(directory) / 'mcp.html'
        asset.write_text('<html><body>KIDSic map</body></html>')
        app = create_app(service, ui_path=asset, rag_service=rag_service)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app),
                                         base_url='http://localhost') as http:
                async with streamable_http_client('http://localhost/mcp',
                                                   http_client=http) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        initialized = await session.initialize()
                        yield session, initialized


class McpServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_rag_tool_returns_citable_context_without_map_metadata(self):
        from KIDSic.dto.rag import RagContext, RagQuery, RagMatch
        query = RagQuery(city='Zagreb', name='Bajka', topics=['programs'])
        context = RagContext(criteria=query, status='no_evidence',total_matches=1,
            matches=[RagMatch(feature_id='00000000-0000-0000-0000-000000000001',kindergarten_id='synthetic',
                name='Synthetic Bajka',location_name='Synthetic object',address=None,city='Zagreb')],
            notice='Nema relevantnog dokaza.')
        rag = SimpleNamespace(retrieve=AsyncMock(return_value=context))
        locations = SimpleNamespace(list_locations=AsyncMock())
        async with connected(locations, rag) as (session, _):
            tools = (await session.list_tools()).tools
            tool = next(t for t in tools if t.name == 'dohvati_kontekst_vrtica')
            self.assertEqual(tool.inputSchema['required'],['city','name'])
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertIsNone(tool.meta)
            result = await session.call_tool(tool.name, query.model_dump())
            self.assertFalse(result.isError)
            self.assertEqual(result.structuredContent,context.model_dump(mode='json'))
            self.assertIn('Nema relevantnog dokaza',result.content[0].text)
            self.assertIsNone(result.meta)
        rag.retrieve.assert_awaited_once_with(query)
        locations.list_locations.assert_not_awaited()

    async def test_rag_invalid_calls_never_access_service_and_errors_allow_recovery(self):
        rag = SimpleNamespace(retrieve=AsyncMock())
        valid = dict(city='Zagreb',name='Bajka',topics=['programs'])
        async with connected(SimpleNamespace(list_locations=AsyncMock()),rag) as (session,_):
            for args in ({},dict(valid,city='Split'),dict(valid,name=' '),dict(valid,topics=[]),
                         dict(valid,topics=['jelovnik']),dict(valid,question='Koji su programi?'),
                         dict(valid,feature_id='invented'),dict(valid,extra='unknown')):
                result = await session.call_tool('dohvati_kontekst_vrtica',args)
                self.assertTrue(result.isError)
                self.assertIn('invalid_arguments',result.content[0].text)
                self.assertIn('Primjer:',result.content[0].text)
            rag.retrieve.assert_not_awaited()
            rag.retrieve.side_effect = RuntimeError('private diagnostic')
            with self.assertLogs('KIDSic.api.rag_tools',level='ERROR'):
                result = await session.call_tool('dohvati_kontekst_vrtica',valid)
            self.assertTrue(result.isError)
            self.assertIn('unavailable',result.content[0].text)
            self.assertNotIn('private diagnostic',result.content[0].text)

    async def test_discovery_links_required_city_tool_to_html_resource(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, initialized):
            self.assertIn('ALWAYS', initialized.instructions)
            self.assertIn('ask the user', initialized.instructions)
            tools = (await session.list_tools()).tools
            self.assertEqual([tool.name for tool in tools], ['prikazi_vrtice', 'dohvati_kontekst_vrtica'])
            tool = tools[0]
            self.assertEqual(tool.inputSchema['required'], ['city'])
            self.assertNotIn('default', tool.inputSchema['properties']['city'])
            self.assertEqual(set(tool.inputSchema['properties']), {'city', 'name', 'provider_kind', 'area', 'age_months', 'program', 'include_unknown',
                              'near', 'radius_m'})
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
                'city': 'Rijeka', 'name': '', 'provider_kind': None, 'area': '', 'age_months': None, 'program': '', 'include_unknown': True, 'near': None, 'radius_m': None,
                'metadata': payload.metadata.model_dump(mode='json'),
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

    async def test_area_and_follow_ups_send_full_criteria_without_server_side_inheritance(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        calls = [
            {'city':'Varaždinu','name':' Bajka ','provider_kind':'private','area':' Banfica '},
            {'city':'Varaždin','name':'Bajka','provider_kind':'private','area':'Centar'},
            {'city':'Varaždin','name':'Bajka','provider_kind':'private','area':''},
            {'city':'Rijeka','area':'Zamet'},
            {'city':'Zagreb'},
        ]
        async with connected(service) as (session, _):
            for arguments in calls:
                service.list_locations.reset_mock()
                result = await session.call_tool('prikazi_vrtice', arguments)
                self.assertFalse(result.isError)
                service.list_locations.assert_awaited_once()
                query = service.list_locations.await_args.args[0]
                self.assertEqual(query.area, arguments.get('area', '').strip())
                self.assertEqual(query.q, arguments.get('name', '').strip())
                self.assertEqual(query.provider_kind, arguments.get('provider_kind'))
                self.assertEqual(result.structuredContent['area'], query.area)
                if query.area:
                    self.assertIn('nula rezultata ne znači', result.content[0].text)
                    self.assertIn('Nemoj', result.content[0].text)

    async def test_invalid_areas_and_area_without_city_never_read_database(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, _):
            missing = await session.call_tool('prikazi_vrtice', {'area':'Banfica'})
            self.assertTrue(missing.isError)
            self.assertIn('U kojem gradu', missing.content[0].text)
            for area in (None, 123, True, [], ['Banfica','Centar'], {}, 'x'*201):
                result = await session.call_tool('prikazi_vrtice', {'city':'Varaždin','area':area})
                self.assertTrue(result.isError)
                self.assertIn('Područje (area)', result.content[0].text)
        service.list_locations.assert_not_awaited()

    async def test_age_and_program_preserve_full_criteria_and_explicit_confirmed_only_choice(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=empty_collection()))
        async with connected(service) as (session, _):
            for age in (0,18,24,30,216,None):
                arguments = {'city':'Varaždinu','name':'Bajka','area':'Centar',
                    'provider_kind':'private','age_months':age,'program':' Montessori ','include_unknown':False}
                result = await session.call_tool('prikazi_vrtice',arguments)
                self.assertFalse(result.isError)
                self.assertEqual(result.structuredContent['age_months'],age)
                self.assertEqual(result.structuredContent['program'],'Montessori')
                self.assertFalse(result.structuredContent['include_unknown'])
                query = service.list_locations.await_args.args[0]
                self.assertEqual((query.city,query.q,query.area,query.provider_kind,query.age_months,query.program,query.include_unknown),
                                 ('Varaždin','Bajka','Centar','private',age,'Montessori',False))
                self.assertIn('nije dokaz',result.content[0].text)
            result = await session.call_tool('prikazi_vrtice',{'city':'Rijeka'})
            self.assertIsNone(result.structuredContent['age_months'])
            self.assertEqual(result.structuredContent['program'],'')
            self.assertTrue(result.structuredContent['include_unknown'])

    async def test_invalid_age_program_unknown_flag_and_missing_city_never_read_database(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, _):
            for key, values, message in (
                ('age_months',(-1,217,24.0,True,'24',[24],{}),'age_months'),
                ('program',(None,True,['Montessori'],{},'x'*201),'Program'),
                ('include_unknown',(None,'false',1,[],{}),'include_unknown'),
            ):
                for value in values:
                    result = await session.call_tool('prikazi_vrtice',{'city':'Zagreb',key:value})
                    self.assertTrue(result.isError)
                    self.assertIn(message,result.content[0].text)
            result = await session.call_tool('prikazi_vrtice',{'age_months':24,'program':'Montessori'})
            self.assertTrue(result.isError)
            self.assertIn('U kojem gradu',result.content[0].text)
        service.list_locations.assert_not_awaited()

    async def test_radius_search_passes_the_point_and_reports_straight_line_scope(self):
        service = SimpleNamespace(list_locations=AsyncMock(return_value=LocationCollection(features=[], metadata={
            'total': 0, 'mapped': 0, 'unmapped': 0, 'scope': 'radius'})))
        async with connected(service) as (session, _):
            result = await session.call_tool('prikazi_vrtice', {
                'city': 'Zagreb', 'provider_kind': 'municipal', 'near': [15.9775, 45.8131], 'radius_m': 1000})
            self.assertFalse(result.isError)
            query = service.list_locations.await_args.args[0]
            self.assertEqual((query.near, query.radius_m, query.provider_kind), ((15.9775, 45.8131), 1000, 'municipal'))
            self.assertEqual((result.structuredContent['near'], result.structuredContent['radius_m']),
                             ([15.9775, 45.8131], 1000))
            self.assertEqual(result.structuredContent['metadata']['scope'], 'radius')
            self.assertIn('Zračno do 1000 m', result.content[0].text)
            self.assertIn('Predloži veći radijus', result.content[0].text)
            plain = await session.call_tool('prikazi_vrtice', {'city': 'Zagreb'})
            self.assertIsNone(plain.structuredContent['near'])
            self.assertIsNone(plain.structuredContent['radius_m'])

    async def test_invalid_radius_arguments_never_read_database(self):
        service = SimpleNamespace(list_locations=AsyncMock())
        async with connected(service) as (session, _):
            for arguments in ({'near': [15.98, 45.81]}, {'radius_m': 1000},
                              {'near': [15.98], 'radius_m': 1000}, {'near': [181, 45], 'radius_m': 1000},
                              {'near': ['15.98', '45.81'], 'radius_m': 1000}, {'near': [True, 45], 'radius_m': 1000},
                              {'near': 'Trg bana Jelačića', 'radius_m': 1000},
                              {'near': [15.98, 45.81], 'radius_m': 0}, {'near': [15.98, 45.81], 'radius_m': 1000.5},
                              {'near': [15.98, 45.81], 'radius_m': '1000'}):
                with self.subTest(arguments=arguments):
                    result = await session.call_tool('prikazi_vrtice', {'city': 'Zagreb', **arguments})
                    self.assertTrue(result.isError)
                    self.assertIn('odabere točku na karti', result.content[0].text)
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
            yield service, SimpleNamespace(retrieve=AsyncMock())
            events.append('close')

        with TemporaryDirectory() as directory:
            asset = Path(directory) / 'mcp.html'
            asset.write_text('<html>map</html>')
            with patch('KIDSic.api.mcp_server.Settings.from_env'), \
                 patch('KIDSic.api.mcp_server.DependencyService') as dependencies:
                dependencies.return_value.conversation_services = locations
                app = create_app(ui_path=asset)
                async with app.router.lifespan_context(app):
                    self.assertEqual(events, ['open'])
                self.assertEqual(events, ['open', 'close'])
