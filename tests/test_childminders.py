"""CSV, resource identity and normalized childminder contracts use synthetic contacts."""
import json
from pathlib import Path
import unittest

import httpx

from KIDSic.config.settings import Settings
from KIDSic.dto.ckan import CkanResource
from KIDSic.exceptions import CkanResponseError, SourceImportError
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.integrations.concrete.ckan import CkanClient
from KIDSic.services.concrete.kindergarten_normalizer import normalize_records

FIXTURES = Path(__file__).parent / 'fixtures'


class ChildminderTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_selects_pinned_csv_and_parses_bom_quotes_and_contacts(self):
        package = json.loads((FIXTURES / 'ckan_childminders.json').read_text())
        # Another CSV must never be substituted for the resource selected by the user.
        package['result']['resources'].append({
            'id': 'other-csv', 'url': 'https://example.invalid/other.csv', 'format': 'CSV'})
        requests = []

        def respond(request):
            requests.append(request)
            if request.url.path.endswith('package_show'):
                return httpx.Response(200, json=package)
            return httpx.Response(200, content=(FIXTURES / 'varazdin_childminders.csv').read_bytes())

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            service = SourceServiceFactory(Settings(database_url='postgresql://localhost/unused')).create(
                http, source_keys=['varazdin-childminders'])
            result = await service.preview_import()
            self.assertEqual(result['sources'][0]['records'], 2)
            client = CkanClient(http)
            records = await client.download_records(CkanResource.model_validate(package['result']['resources'][0]))
        rows = normalize_records(records, 'varazdin-childminders')
        self.assertEqual(requests[0].url.params['id'], 'grad-varazdin-dadilje')
        self.assertEqual(str(requests[1].url), 'https://example.invalid/childminders.csv')
        self.assertEqual(rows[0].source_key, '00000001')
        self.assertEqual(rows[0].oib, '00123456789')
        self.assertEqual(rows[0].phone, '042/000001; 099/000001')
        self.assertEqual((rows[0].address, rows[0].settlement, rows[0].postal_code), ('Primjer 1', 'Varaždin', '42000'))
        self.assertEqual((rows[0].scope, rows[0].provider_kind), ('institution', 'childminder'))
        self.assertIsNone(rows[0].longitude)
        self.assertIsNone(rows[1].oib)
        self.assertEqual(rows[1].address, 'Hrašćica, Primjer 2')
        self.assertEqual(rows[1].raw_data['OIB'], '00987654321   00987654322')
        # Contact/address edits do not change the trade's source identity.
        changed = normalize_records([{**records[0], 'Adresa sjedišta': 'Primjer 99'}], 'varazdin-childminders')[0]
        self.assertEqual(changed.source_key, rows[0].source_key)
        for changes in ({'Matični broj': ''}, {'Mjesto sjedišta': 'Varaždin'}, {'OIB': 'invalid'}):
            with self.assertRaises(SourceImportError):
                normalize_records([{**records[0], **changes}], 'varazdin-childminders')
        with self.assertRaises(SourceImportError):
            normalize_records([records[0], records[0]], 'varazdin-childminders')

    async def test_changed_or_missing_resource_is_rejected(self):
        for change in ({'id': 'replacement'}, {'format': 'JSON'}, {'state': 'deleted'}):
            package = json.loads((FIXTURES / 'ckan_childminders.json').read_text())
            package['result']['resources'][0].update(change)
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=package))) as http:
                service = SourceServiceFactory(Settings(database_url='postgresql://localhost/unused')).create(
                    http, source_keys=['varazdin-childminders'])
                with self.assertRaises(SourceImportError):
                    await service.preview_sources()

    async def test_csv_corruption_and_size_limits_fail_explicitly(self):
        resource = CkanResource(id='csv', url='https://example.invalid/data.csv', format='text/csv')
        for body in (b'\xff', b'a;a\n1;2', b'a;b\n1', b'a;b\n1;2;3', b'a;b\n"unterminated', b''):
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body))) as http:
                with self.assertRaises(CkanResponseError):
                    await CkanClient(http).download_records(resource)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b'a;b\n1;2'))) as http:
            with self.assertRaises(CkanResponseError):
                await CkanClient(http, max_bytes=4).download_records(resource)
