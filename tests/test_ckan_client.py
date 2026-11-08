"""The reference client's error contract, plus KIDSic's slug ID/JSON downloads."""

import copy
import json
import unittest
from pathlib import Path

import httpx

from KIDSic.dto.ckan import CkanResource
from KIDSic.exceptions import (
    CkanApiError,
    CkanHttpError,
    CkanResponseError,
    CkanTransportError,
)
from KIDSic.integrations.concrete.ckan import CkanClient

FIXTURES = Path(__file__).parent / "fixtures"


class CkanClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.payload = json.loads((FIXTURES / "ckan_national.json").read_text())

    async def test_real_metadata_accepts_slug_id_and_does_not_close_the_injected_client(
        self,
    ):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=self.payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            resources = await CkanClient(
                http, "https://data.gov.hr/ckan/", timeout=2
            ).get_resources("dataset slug")
            self.assertEqual(resources[0].id, "djecji-vrtici")
            self.assertEqual(len(resources), 3)
            self.assertFalse(http.is_closed)
        self.assertEqual(requests[0].url.path, "/ckan/api/3/action/package_show")
        self.assertEqual(requests[0].url.params["id"], "dataset slug")
        self.assertEqual(requests[0].extensions["timeout"]["read"], 2)

    async def test_http_and_action_errors_are_distinct(self):
        for status in (404, 429, 500, 503):
            with self.subTest(status=status):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda request, status=status: httpx.Response(
                            status, text="upstream error"
                        )
                    )
                ) as http:
                    with self.assertRaises(CkanHttpError) as error:
                        await CkanClient(http).get_resources("dataset")
                    self.assertEqual(error.exception.status_code, status)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json={"success": False, "error": {"message": "Not found"}}
                )
            )
        ) as http:
            with self.assertRaises(CkanApiError):
                await CkanClient(http).get_resources("missing")

    async def test_invalid_json_envelopes_and_resource_urls_fail_explicitly(self):
        invalid = [
            [],
            {},
            {"success": "true"},
            {"success": True, "result": {}},
            {"success": True, "result": {"resources": {}}},
        ]
        for field, value in [("id", ""), ("url", "file:///etc/passwd")]:
            payload = copy.deepcopy(self.payload)
            payload["result"]["resources"][0][field] = value
            invalid.append(payload)
        for payload in invalid:
            with self.subTest(payload=payload):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda request, payload=payload: httpx.Response(
                            200, json=payload
                        )
                    )
                ) as http:
                    with self.assertRaises(CkanResponseError):
                        await CkanClient(http).get_package("dataset")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text="<html>proxy error</html>")
            )
        ) as http:
            with self.assertRaises(CkanResponseError):
                await CkanClient(http).get_resources("dataset")

    async def test_transport_failures_have_no_implicit_retries(self):
        for exception in (httpx.ConnectError, httpx.ReadTimeout):
            requests = []

            def fail(request, requests=requests, exception=exception):
                requests.append(request)
                raise exception("unavailable", request=request)

            async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http:
                with self.assertRaises(CkanTransportError):
                    await CkanClient(http).get_package("dataset")
                self.assertFalse(http.is_closed)
            self.assertEqual(len(requests), 1)

    async def test_download_contract_and_response_size_limit(self):
        resource = CkanResource(id="slug", url="https://example.invalid/data.json")
        for body in ({"error": "not an array"}, [1], ["row"]):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request, body=body: httpx.Response(200, json=body)
                )
            ) as http:
                with self.assertRaises(CkanResponseError):
                    await CkanClient(http).download_records(resource)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=b'[{"value":"oversized"}]')
            )
        ) as http:
            with self.assertRaises(CkanResponseError):
                await CkanClient(http, max_bytes=8).download_records(resource)

    async def test_blank_dataset_and_invalid_settings_are_rejected(self):
        async with httpx.AsyncClient() as http:
            with self.assertRaises(ValueError):
                await CkanClient(http).get_resources(" ")
            for timeout in (0, -1, float("nan"), float("inf")):
                with self.assertRaises(ValueError):
                    CkanClient(http, timeout=timeout)
            for url in (
                "file:///tmp/ckan",
                "https://example.invalid/?query=1",
                "https://example.invalid/#fragment",
            ):
                with self.assertRaises(ValueError):
                    CkanClient(http, base_url=url)
