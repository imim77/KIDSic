"""Architecture tests protect dependency direction and replaceable business policies."""
import ast
from pathlib import Path
import unittest
from unittest.mock import AsyncMock

from KIDSic.dto.source import KindergartenRow, SourceDefinition
from KIDSic.services.interfaces.source_parser import SourceRowParser
from KIDSic.services.concrete.source import SourceService
from KIDSic.services.concrete.source_normalizer import SourceRecordNormalizer
from KIDSic.services.concrete.request_parser import RequestParser
from test_sources import source_client

ROOT = Path(__file__).resolve().parents[1] / 'src' / 'KIDSic'


class LayerDependencyTests(unittest.TestCase):
    def test_business_and_contracts_do_not_import_infrastructure_implementations(self):
        paths = [*ROOT.joinpath('services/concrete').rglob('*.py'),
                 *ROOT.joinpath('services/interfaces').rglob('*.py'),
                 *ROOT.joinpath('dao/interfaces').rglob('*.py'),
                 ROOT / 'db/uow/base.py', ROOT / 'db/uow/source.py']
        forbidden = ('asyncpg', 'httpx', 'sqlalchemy', 'starlette', 'mcp',
                     'KIDSic.dao.concrete', 'KIDSic.integrations.concrete', 'KIDSic.factories')
        for path in paths:
            for node in ast.walk(ast.parse(path.read_text())):
                modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else (
                    [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    self.assertFalse(any(module == item or module.startswith(item + '.') for item in forbidden),
                                     f'{path.relative_to(ROOT)} imports {module}')

    def test_persistence_never_calls_presentation_or_business_services(self):
        for path in ROOT.joinpath('dao').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or '').startswith(('KIDSic.api', 'KIDSic.services', 'KIDSic.factories')),
                                     str(path))

    def test_presentation_uses_services_without_database_drivers(self):
        for package in ('api','commands'):
            for path in ROOT.joinpath(package).rglob('*.py'):
                for node in ast.walk(ast.parse(path.read_text())):
                    modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else (
                        [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
                    for module in modules:
                        self.assertFalse(module.startswith(('asyncpg','sqlalchemy','KIDSic.dao','KIDSic.db')),
                                         f'{path.relative_to(ROOT)} imports {module}')

    def test_legacy_mcp_entry_point_still_uses_the_same_application(self):
        from KIDSic.mcp.server import create_app as legacy
        from KIDSic.api.mcp_server import create_app
        self.assertIs(legacy, create_app)

    def test_request_parser_needs_only_catalogue_values(self):
        parser = RequestParser()
        criteria = parser.parse_city_age('Dijete od 2 godine iz Varaždina',
                                        [{'city_key':'varazdin','city_aliases':['varazdina']}])
        self.assertEqual(criteria, {'city':'varazdin','age_months':24})
        self.assertEqual(parser.parse_area('na Banfici', [{'name':'Banfica'}]), 'Banfica')

    def test_request_parser_rejects_unsupported_cities_even_in_a_legacy_catalogue(self):
        parser = RequestParser()
        for city in ('split', 'osijek', 'sesvete'):
            with self.subTest(city=city), self.assertRaisesRegex(ValueError, 'Zagreb, Varaždin i Rijeka'):
                parser.parse_city_age(f'Dijete od 2 godine iz {city}',
                                      [{'city_key': city, 'city_aliases': []}])
        self.assertEqual(parser.parse_city_age('Dijete od 2 godine iz Rijeke',
            [{'city_key': 'rijeka', 'city_aliases': ['rijeke']}]), {'city': 'rijeka', 'age_months': 24})


class ExtensibleSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_new_schema_can_be_injected_without_changing_service_or_normalizer(self):
        class ExampleParser(SourceRowParser):
            def parse(self, record):
                return KindergartenRow(source_key=record['id'], raw_data=record,
                    name='Example',location_name='Example',settlement='Varaždin',address='Example 1',
                    municipality='varazdin')
        client = source_client()
        client.download_records = AsyncMock(return_value=[{'id':'one'},{'id':'two'}])
        definition = SourceDefinition('example','https://data.gov.hr/ckan','example','custom-schema')
        service = SourceService({'example':client}, [definition],
                                normalizer=SourceRecordNormalizer({'custom-schema':ExampleParser()}))
        result = await service.preview_import()
        self.assertEqual(result['sources'][0]['records'],2)
