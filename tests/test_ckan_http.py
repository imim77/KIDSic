"""Optional real-socket checks against the committed Postman simulation."""
import os
import unittest

import httpx

from KIDSic.config.settings import Settings
from KIDSic.exceptions import CkanApiError, CkanHttpError, CkanResponseError, CkanTransportError, SourceImportError
from KIDSic.factories.source import SourceServiceFactory
from KIDSic.integrations.concrete.ckan import CkanClient


@unittest.skipUnless(os.getenv('KIDSIC_CKAN_SIMULATION_URL'), 'Start the CKAN Postman simulation')
class CkanHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_metadata_and_download_through_real_http(self):
        url = os.environ['KIDSIC_CKAN_SIMULATION_URL']
        settings = Settings(database_url='postgresql://localhost/unused', ckan_base_url=url,
                            ckan_zagreb_base_url=url)
        async with httpx.AsyncClient() as http:
            service = SourceServiceFactory(settings).create(http, source_keys=['national', 'zagreb-municipal', 'zagreb-other'])
            self.assertEqual(len((await service.preview_sources())['sources']), 3)
            result = await service.preview_import()
        self.assertEqual([s['records'] for s in result['sources']], [1, 2, 1])

    async def test_real_http_error_boundaries_and_download_failure(self):
        url = os.environ['KIDSIC_CKAN_SIMULATION_URL']
        async with httpx.AsyncClient() as http:
            client = CkanClient(http, url, timeout=0.05)
            for dataset, expected in [('http-error', CkanHttpError), ('api-error', CkanApiError),
                                      ('html', CkanResponseError), ('slow', CkanTransportError)]:
                with self.subTest(dataset=dataset), self.assertRaises(expected):
                    await client.get_package(dataset)
            package = await client.get_package('broken-download')
            with self.assertRaises(CkanHttpError):
                await client.download_records(package.resources[0])
            settings = Settings(database_url='postgresql://localhost/unused', ckan_base_url=url,
                                ckan_dataset_id='empty')
            with self.assertRaises(SourceImportError):
                await SourceServiceFactory(settings).create(http, source_keys=['national']).preview_import()
